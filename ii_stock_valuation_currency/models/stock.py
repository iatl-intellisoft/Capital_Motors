from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import OrderedSet


class ProductCategory(models.Model):
    _inherit = 'product.category'

    adjustment_account = fields.Many2one('account.account', string='Inventory Adjust Account')


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    stock_currency_id = fields.Many2one('res.currency', string='Stock Valuation Currency', required=True,
                                        default=lambda self: self.env.company.stock_currency_id)

    currency_cost = fields.Monetary('Currency Cost', currency_field='stock_currency_id', digits=(10, 2),
                                    compute="compute_currency_cost")

    @api.depends('product_id', 'value', 'inventory_quantity', 'stock_currency_id')
    def compute_currency_cost(self):
        for quant in self:
            quant.currency_cost = 0.0
            quant.currency_id = quant.company_id.currency_id
            # If the user didn't enter a location yet while enconding a quant.
            if not quant.location_id:
                quant.value = 0
                return

            if not quant.location_id._should_be_valued() or \
                    (quant.owner_id and quant.owner_id != quant.company_id.partner_id):
                quant.value = 0
                continue
            if quant.product_id.cost_method == 'fifo':
                quantity = quant.product_id.with_company(quant.company_id).quantity_svl
                if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                    quant.value = 0.0
                    continue
                average_cost = quant.product_id.with_company(quant.company_id).currency_value_svl / quantity
                quant.currency_cost = quant.quantity * average_cost
            if quant.product_id.cost_method == 'average':
                quant.currency_cost = quant.quantity * quant.product_id.with_company(quant.company_id).cost_price_usd
            if quant.product_id.cost_method == 'standard':
                quant.currency_cost = quant.quantity * quant.product_id.with_company(
                    quant.company_id).standard_price_currency


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def button_validate(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'move_type': 'entry',
            }
            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                remaining_qty = sum(line.move_id.stock_valuation_layer_ids.mapped('remaining_qty'))
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]

                # Prorate the value at what's still in stock
                currency_rate = self.env['res.currency'].search([('id', '=', self.env.company.stock_currency_id.id)], limit=1).rate
                cost_to_add = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost
                usd_cost_to_add = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost * currency_rate
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    valuation_layer = self.env['stock.valuation.layer'].create({
                        'value': cost_to_add,
                        'unit_cost': 0,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'stock_valuation_layer_id': linked_layer.id,
                        'description': cost.name,
                        'stock_move_id': line.move_id.id,
                        'product_id': line.move_id.product_id.id,
                        'stock_landed_cost_id': cost.id,
                        'company_id': cost.company_id.id,
                        'inventory_value_usd': usd_cost_to_add,
                        'unit_price_usd': 0,
                        'remaining_value_usd': 0,
                    })
                    linked_layer.remaining_value += cost_to_add
                    linked_layer.remaining_value_usd += usd_cost_to_add
                    valuation_layer_ids.append(valuation_layer.id)
                # Update the AVCO
                product = line.move_id.product_id
                if product.cost_method == 'average':
                    cost_to_add_byproduct[product] += cost_to_add
                # Products with manual inventory valuation are ignored because they do not need to create journal entries.
                # Test Comment The 2 Follwing lines
                #if product.valuation != "real_time":
                #   continue
                # `remaining_qty` is negative if the move is out and delivered proudcts that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

            # batch standard price computation avoid recompute quantity_svl at each iteration
            products = self.env['product.product'].browse(p.id for p in cost_to_add_byproduct.keys())
            for product in products:  # iterate on recordset to prefetch efficiently quantity_svl
                if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                    product.with_company(cost.company_id).sudo().with_context(disable_auto_svl=True).standard_price += cost_to_add_byproduct[product] / product.quantity_svl
                    #product.with_company(cost.company_id).sudo().with_context(disable_auto_svl=True).standard_price_currency += ((cost_to_add_byproduct[product] / product.quantity_svl) * currency_rate)

            move_vals['stock_valuation_layer_ids'] = [(6, None, valuation_layer_ids)]
            # We will only create the accounting entry when there are defined lines (the lines will be those linked to products of real_time valuation category).
            cost_vals = {'state': 'done'}
            if move_vals.get("line_ids"):
                move = move.create(move_vals)
                cost_vals.update({'account_move_id': move.id})
            cost.write(cost_vals)
            if cost.account_move_id:
                move._post()

            if cost.vendor_bill_id and cost.vendor_bill_id.state == 'posted' and cost.company_id.anglo_saxon_accounting:
                all_amls = cost.vendor_bill_id.line_ids | cost.account_move_id.line_ids
                for product in cost.cost_lines.product_id:
                    accounts = product.product_tmpl_id.get_product_accounts()
                    input_account = accounts['stock_input']
                    all_amls.filtered(lambda aml: aml.account_id == input_account and not aml.reconciled).reconcile()

        return True


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit_usd(self):
        """ Returns the unit price to value this stock move """
        self.ensure_one()
        price_unit_usd = self.price_unit * self.env['res.currency'].search(
            [('id', '=', self.env.company.stock_currency_id.id)], limit=1).rate
        precision = self.env['decimal.precision'].precision_get('Product Price')
        # If the move is a return, use the original move's price unit.
        if self.origin_returned_move_id and self.origin_returned_move_id.sudo().stock_valuation_layer_ids:
            price_unit_usd = self.origin_returned_move_id.sudo().stock_valuation_layer_ids[-1].unit_price_usd
        return not float_is_zero(price_unit_usd, precision) and price_unit_usd or self.product_id.cost_price_usd

    def product_price_update_before_done(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        std_foreign_price_update = {}
        for move in self.filtered(lambda move: move._is_in() and move.with_company(move.company_id).product_id.cost_method == 'average'):
            product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)

            qty = forced_qty or qty_done
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
                new_foreign_std_price = move._get_price_unit_usd()
            elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                    float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
                new_foreign_std_price = move._get_price_unit_usd()
            else:
                # Get the standard price
                amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.with_company(move.company_id).standard_price
                amount_unit_foreign = std_foreign_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.with_company(move.company_id).cost_price_usd
                new_std_price = ((amount_unit * product_tot_qty_available) + (move._get_price_unit() * qty)) / (product_tot_qty_available + qty)
                new_foreign_std_price = ((amount_unit_foreign * product_tot_qty_available) + (move._get_price_unit_usd() * qty)) / (product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty_done
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write({'standard_price': new_std_price,'cost_price_usd':new_foreign_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

        # adapt standard price on incomming moves if the product cost_method is 'fifo'
        for move in self.filtered(lambda move:
                                  move.with_company(move.company_id).product_id.cost_method == 'fifo'
                                  and float_is_zero(move.product_id.sudo().quantity_svl, precision_rounding=move.product_id.uom_id.rounding)):
            move.product_id.with_company(move.company_id.id).sudo().write({'standard_price': move._get_price_unit(),'cost_price_usd':move._get_price_unit_usd()})

    def _account_entry_move(self, qty, description, svl_id, cost, eur_cost):
        """ Accounting Valuation Entries """
        self.ensure_one()
        am_vals = []
        if self.product_id.type != 'product':
            # no stock valuation for consumable products
            return am_vals
        if self.restrict_partner_id and self.restrict_partner_id != self.company_id.partner_id:
            # if the move isn't owned by the company, we don't make any valuation
            return am_vals

        company_from = self._is_out() and self.mapped('move_line_ids.location_id.company_id') or False
        company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False

        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if self._is_in():
            if self._is_returned(valued_type='in'):
                am_vals.append(self.with_company(company_to)._prepare_account_move_vals(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost, eur_cost))
            else:
                am_vals.append(self.with_company(company_to)._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost, eur_cost))

        # Create Journal Entry for products leaving the company
        if self._is_out():
            cost = -1 * cost
            eur_cost = -1 * eur_cost
            if self._is_returned(valued_type='out'):
                am_vals.append(self.with_company(company_from)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost, eur_cost))
            else:
                am_vals.append(self.with_company(company_from)._prepare_account_move_vals(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost, eur_cost))

        if self.company_id.anglo_saxon_accounting:
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            if self._is_dropshipped():
                if cost > 0:
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost, eur_cost))
                else:
                    cost = -1 * cost
                    eur_cost = -1 * eur_cost
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost, eur_cost))
            elif self._is_dropshipped_returned():
                if cost > 0:
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost, eur_cost))
                else:
                    cost = -1 * cost
                    eur_cost = -1 * eur_cost
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost, eur_cost))


        if self._is_internal():
            if self.location_id.usage == 'internal' and self.location_dest_id.usage == 'transit':
                cost = -1 * cost
                eur_cost = -1 * eur_cost
                am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_valuation, self.location_dest_id.valuation_out_account_id.id, journal_id, qty, description, svl_id, cost, eur_cost))

            if self.location_id.usage == 'transit' and self.location_dest_id.usage == 'internal':
                am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(self.location_id.valuation_out_account_id.id, acc_valuation, journal_id, qty, description, svl_id, cost, eur_cost))

        return am_vals

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, svl_id, description, eur_cost):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.company_id.currency_id.round(cost)
        credit_value = debit_value

        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        eur_rate = self.env['res.currency'].search([('id', '=', self.env.company.stock_currency_id.id)]).rate
        new_lines = []
        if eur_rate > 0.0:
            new_sdg_value = eur_cost / eur_rate
        if self._is_in():
            new_sdg_value = debit_value
        diff = new_sdg_value - debit_value
        adjustment_account = self.product_id.categ_id.adjustment_account.id
        if diff > 0.0:
            debit_line_vals = {
                'name': description + 'Adjustment with ' + self.env.company.stock_currency_id.name + 'Rate' + str(
                    1 / eur_rate),
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': valuation_partner_id,
                'debit': diff,
                'account_id': credit_account_id,
            }
            new_lines.append(debit_line_vals)
            credit_line_vals = {
                'name': description + 'Adjustment with ' + self.env.company.stock_currency_id.name + ' Rate = ' + str(
                    1 / eur_rate),
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': valuation_partner_id,
                'credit': diff,
                'account_id': adjustment_account,
            }
            new_lines.append(credit_line_vals)
        elif diff < 0.0:
            debit_line_vals = {
                'name': description + 'Adjustment with ' + self.env.company.stock_currency_id.name + 'Rate' + str(
                        1 / eur_rate),
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': valuation_partner_id,
                'debit': abs(diff),
                'account_id': adjustment_account,
            }
            new_lines.append(debit_line_vals)
            credit_line_vals = {
                'name': description + 'Adjustment with ' + self.env.company.stock_currency_id.name + ' Rate = ' + str(
                        1 / eur_rate),
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': valuation_partner_id,
                'credit': abs(diff),
                'account_id': credit_account_id,
            }
            new_lines.append(credit_line_vals)
        new_lines = [(0, 0, line) for line in new_lines]

        res = [(0, 0, line_vals) for line_vals in self._generate_valuation_lines_data(valuation_partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description, eur_cost).values()]

        return res, new_lines

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description, eur_cost):
        # This method returns a dictionary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
        self.ensure_one()
        eur_rate = 1
        new_sdg_value = 0
        # raise UserError(eur_cost)
        eur_rate = self.env['res.currency'].search([('id', '=', self.env.company.stock_currency_id.id)]).rate
        if eur_rate > 0.0:
            new_sdg_value = eur_cost / eur_rate
        if self._is_in():
            new_sdg_value = debit_value
        #diff = new_sdg_value - debit_value
        #adjustment_account = self.product_id.categ_id.adjustment_account.id

        debit_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'balance': new_sdg_value,
            'account_id': debit_account_id,
            'amount_currency': eur_cost,
            'currency_id': self.env.company.stock_currency_id.id,
        }

        credit_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'balance': -new_sdg_value,
            'account_id': credit_account_id,
            'amount_currency': -eur_cost,
            'currency_id': self.env.company.stock_currency_id.id,
        }

        rslt = {'credit_line_vals': credit_line_vals, 'debit_line_vals': debit_line_vals}
        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.env.context.get('price_diff_account')
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))

            rslt['price_diff_line_vals'] = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'credit': diff_amount > 0 and diff_amount or 0,
                'debit': diff_amount < 0 and -diff_amount or 0,
                'account_id': price_diff_account.id,
            }
            
        purchase_currency = self.purchase_line_id.currency_id
        if not self.purchase_line_id or purchase_currency == self.company_id.currency_id:
            return rslt
        svl = self.env['stock.valuation.layer'].browse(svl_id)
        if not svl.account_move_line_id:
            # Do not use price_unit since we want the price tax excluded. And by the way, qty
            # is in the UOM of the product, not the UOM of the PO line.
            purchase_price_unit = (
                self.purchase_line_id.price_subtotal / self.purchase_line_id.product_uom_qty
                if self.purchase_line_id.product_uom_qty
                else self.purchase_line_id.price_unit
            )
            currency_move_valuation = purchase_currency.round(purchase_price_unit * abs(qty))
            rslt['credit_line_vals']['amount_currency'] = rslt['credit_line_vals']['balance'] < 0 and -currency_move_valuation or currency_move_valuation
            rslt['debit_line_vals']['amount_currency'] = rslt['debit_line_vals']['balance'] < 0 and -currency_move_valuation or currency_move_valuation
            rslt['debit_line_vals']['currency_id'] = purchase_currency.id
            rslt['credit_line_vals']['currency_id'] = purchase_currency.id
        else:
            rslt['credit_line_vals']['amount_currency'] = 0
            rslt['debit_line_vals']['amount_currency'] = 0
            rslt['debit_line_vals']['currency_id'] = purchase_currency.id
            rslt['credit_line_vals']['currency_id'] = purchase_currency.id
            if not svl.price_diff_value:
                return rslt
            # The idea is to force using the company currency during the reconciliation process
            rslt['debit_line_vals_curr'] = {
                'name': _("Currency exchange rate difference"),
                'product_id': self.product_id.id,
                'quantity': 0,
                'product_uom_id': self.product_id.uom_id.id,
                'partner_id': partner_id,
                'balance': 0,
                'account_id': debit_account_id,
                'currency_id': purchase_currency.id,
                'amount_currency': -svl.price_diff_value,
            }
            rslt['credit_line_vals_curr'] = {
                'name': _("Currency exchange rate difference"),
                'product_id': self.product_id.id,
                'quantity': 0,
                'product_uom_id': self.product_id.uom_id.id,
                'partner_id': partner_id,
                'balance': 0,
                'account_id': credit_account_id,
                'currency_id': purchase_currency.id,
                'amount_currency': svl.price_diff_value,
            }
        return rslt

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost, eur_cost):
        self.ensure_one()
        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        list1, list2  = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, svl_id, description, eur_cost)
        #move_lines  = list1 + list2
        svl = self.env['stock.valuation.layer'].browse(svl_id)
        if self.env.context.get('force_period_date'):
            date = self.env.context.get('force_period_date')
        elif svl.account_move_line_id:
            date = svl.account_move_line_id.date
        else:
            date = fields.Date.context_today(self)
        return {
            'journal_id': journal_id,
            'line_ids': list1 + list2,
            'partner_id': valuation_partner_id,
            'date': date,
            'ref': description,
            'stock_move_id': self.id,
            'stock_valuation_layer_ids': [(6, None, [svl_id])],
            'move_type': 'entry',
        }

    def _get_transfer_move_lines(self):
        """ Returns the `stock.move.line` records of `self` considered as outgoing. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the outgoing records
        :rtype: recordset
        """
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id:
                continue
            if move_line.location_id._should_be_valued() and move_line.location_dest_id._should_be_valued():
                res |= move_line
        #return self.move_line_ids
        return res

    def _is_internal(self):
        """Check if the move should be considered as leaving the company so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is leaving the company else False
        :rtype: bool
        """
        self.ensure_one()
        if self._get_transfer_move_lines():
            return True
        return False

    @api.model
    def _get_valued_types(self):
        """Returns a list of `valued_type` as strings. During `action_done`, we'll call
        `_is_[valued_type]'. If the result of this method is truthy, we'll consider the move to be
        valued.

        :returns: a list of `valued_type`
        :rtype: list
        """
        return ['in', 'out', 'internal', 'dropshipped', 'dropshipped_returned']

    def _create_internal_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            if move.location_id.usage == 'internal' and move.location_dest_id.usage == 'transit':
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_transfer_move_lines()
                valued_quantity = 0
                for valued_move_line in valued_move_lines:
                    valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
                if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                    continue
                svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id)
                svl_vals.update(move._prepare_common_svl_vals())
                if forced_quantity:
                    svl_vals[
                        'description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
                svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
                svl_vals_list.append(svl_vals)
            if move.location_id.usage == 'transit' and move.location_dest_id.usage == 'internal':
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_transfer_move_lines()
                valued_quantity = 0
                for valued_move_line in valued_move_lines:
                    valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
                unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
                if move.product_id.cost_method == 'standard':
                    unit_cost = move.product_id.standard_price
                svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
                svl_vals.update(move._prepare_common_svl_vals())
                if forced_quantity:
                    svl_vals[
                        'description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
                svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)


class StockValuation(models.Model):
    _inherit = 'stock.valuation.layer'

    stock_currency_id = fields.Many2one('res.currency', string='Stock Valuation Currency', required=True,
                                        default=lambda self: self.env.company.stock_currency_id)
    inventory_value_usd = fields.Monetary('Value in Currency', currency_field='stock_currency_id', readonly=True,
                                          digits=(10, 2))
    unit_price_usd = fields.Monetary('Unit Price Currency', currency_field='stock_currency_id', store=True,
                                     readonly=True, digits=(10, 2))
    remaining_value_usd = fields.Monetary('Remaining Value Currency', currency_field='stock_currency_id', store=True)

    @api.model
    def create(self, vals):
        res = super(StockValuation, self).create(vals)
        currency_rate = self.env['res.currency'].search([('id', '=', self.env.company.stock_currency_id.id)],
                                                        limit=1).rate
        if res['unit_price_usd'] == 0.0:
            res['unit_price_usd'] = res['unit_cost'] * currency_rate
        if res['inventory_value_usd'] == 0.0:
            res['inventory_value_usd'] = res['value'] * currency_rate
        if res['inventory_value_usd'] == 0.0:
            res['remaining_value_usd'] = res['remaining_value'] * currency_rate
        return res

    def _validate_accounting_entries(self):
        am_vals = []
        for svl in self:
            if not svl.with_company(svl.company_id).product_id.valuation == 'real_time':
                continue
            if svl.currency_id.is_zero(svl.value):
                continue
            move = svl.stock_move_id
            if not move:
                move = svl.stock_valuation_layer_id.stock_move_id
            am_vals += move.with_company(svl.company_id)._account_entry_move(svl.quantity, svl.description, svl.id, svl.value, svl.inventory_value_usd)
        if am_vals:
            account_moves = self.env['account.move'].sudo().create(am_vals)
            account_moves._post()
        for svl in self:
            # Eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
            if svl.company_id.anglo_saxon_accounting:
                svl.stock_move_id._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=svl.product_id)
