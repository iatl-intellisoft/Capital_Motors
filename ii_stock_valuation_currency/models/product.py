from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_repr
from odoo.exceptions import UserError
from odoo.tools import (
    float_compare,
    float_is_zero,
    float_round,
)


class ProductProduct(models.Model):
    _inherit = "product.product"

    currency_value_svl = fields.Float(compute='_compute_value_svl', compute_sudo=True)
    stock_currency_id = fields.Many2one('res.currency', string='Stock Valuation Currency', required=True,
                                        default=lambda self: self.env.company.stock_currency_id)
    cost_price_usd = fields.Monetary('Average Cost', currency_field='stock_currency_id', digits=(10, 2),
                                     compute='compute_average_cost')
    standard_price_currency = fields.Monetary(string='Standard Cost', currency_field='stock_currency_id')

    # -------------------------------------------------------------------------
    # SVL creation helpers
    # -------------------------------------------------------------------------
    def _prepare_out_svl_vals(self, quantity, company):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        company_id = self.env.context.get('force_company', self.env.company.id)
        company = self.env['res.company'].browse(company_id)
        currency = company.currency_id
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals = {
            'product_id': self.id,
            'value': currency.round(quantity * self.standard_price),
            'unit_cost': self.standard_price,
            'quantity': quantity,
            'inventory_value_usd': quantity * self.standard_price_currency,
            'unit_price_usd': -quantity * self.standard_price_currency,
        }
        fifo_vals = self._run_fifo(abs(quantity), company)
        vals['remaining_qty'] = fifo_vals.get('remaining_qty')
        # In case of AVCO, fix rounding issue of standard price when needed.
        if self.cost_method == 'average':
            currency = self.env.company.currency_id
            rounding_error = currency.round(self.standard_price * self.quantity_svl - self.value_svl)
            rounding_error_currency = currency.round(self.cost_price_usd * self.quantity_svl - self.currency_value_svl)
            if rounding_error:
                # If it is bigger than the (smallest number of the currency * quantity) / 2,
                # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                if abs(rounding_error) <= (abs(quantity) * currency.rounding) / 2:
                    vals['value'] += rounding_error
                    vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                        '+' if rounding_error > 0 else '',
                        float_repr(rounding_error, precision_digits=currency.decimal_places),
                        currency.symbol
                    )
            vals.update({
                'inventory_value_usd': quantity * self.cost_price_usd,
                'unit_price_usd': self.cost_price_usd,
            })
            if rounding_error_currency:
                # If it is bigger than the (smallest number of the currency * quantity) / 2,
                # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                if abs(rounding_error_currency) <= (abs(quantity) * currency.rounding) / 2:
                    vals['value'] += rounding_error
                    vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                        '+' if rounding_error > 0 else '',
                        float_repr(rounding_error, precision_digits=currency.decimal_places),
                        currency.symbol
                    )
        if self.cost_method == 'fifo':
            vals.update(fifo_vals)
        return vals

    def _prepare_in_svl_vals(self, quantity, unit_cost):
        """Prepare the values for a stock valuation layer created by a receipt.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :param unit_cost: the unit cost to value `quantity`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        currency_rate = self.env['res.currency'].search([('id', '=', self.env.company.stock_currency_id.id)], limit=1).rate
        company_id = self.env.context.get('force_company', self.env.company.id)
        company = self.env['res.company'].browse(company_id)
        value = company.currency_id.round(unit_cost * quantity)
        return {
            'product_id': self.id,
            'value': value,
            'unit_cost': unit_cost,
            'inventory_value_usd': value * currency_rate,
            'unit_price_usd': unit_cost * currency_rate,
            'quantity': quantity,
            'remaining_qty': quantity,
            'remaining_value': value,
            'remaining_value_usd': value * currency_rate,
        }

    def _run_fifo(self, quantity, company):
        self.ensure_one()

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity
        candidates = self.env['stock.valuation.layer'].sudo().search([
            ('product_id', '=', self.id),
            ('remaining_qty', '>', 0),
            ('company_id', '=', company.id),
        ])
        new_standard_price = 0
        new_usd_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        tmp_usd_value = 0  # to accumulate the value taken on the candidates
        for candidate in candidates:
            qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)

            candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
            candidate_usd_unit_cost = candidate.remaining_value_usd / candidate.remaining_qty
            new_standard_price = candidate_unit_cost
            new_usd_standard_price = candidate_usd_unit_cost
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_usd_taken_on_candidate = qty_taken_on_candidate * candidate_usd_unit_cost
            value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
            new_remaining_value = candidate.remaining_value - value_taken_on_candidate
            new_usd_remaining_value = candidate.remaining_value_usd - value_usd_taken_on_candidate

            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': new_remaining_value,
                'remaining_value_usd': new_usd_remaining_value,
            }

            candidate.write(candidate_vals)

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate
            tmp_usd_value += value_usd_taken_on_candidate
            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
                    next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
                    new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
                break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and self.cost_method == 'fifo':
            self.sudo().with_company(company.id).with_context(disable_auto_svl=True).standard_price = new_standard_price
            self.sudo().with_company(company.id).with_context(disable_auto_svl=True).standard_price_currency = new_usd_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        vals = {}
        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
            vals = {
                'value': -tmp_value,
                'inventory_value_usd': -tmp_usd_value,
                'unit_cost': tmp_value / quantity,
                'unit_price_usd': tmp_usd_value / quantity,
            }
        else:
            assert qty_to_take_on_candidates > 0
            last_fifo_price = new_standard_price or self.standard_price
            last_fifo_usd_price = new_usd_standard_price or self.standard_price_currency
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            negative_usd_stock_value = last_fifo_usd_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            tmp_usd_value += abs(negative_usd_stock_value)
            vals = {
                'remaining_qty': -qty_to_take_on_candidates,
                'value': -tmp_value,
                'inventory_value_usd': -tmp_usd_value,
                'unit_cost': last_fifo_price,
                'unit_price_usd': last_fifo_usd_price,
            }
        return vals

    def _run_fifo_vacuum(self, company=None):
        """Compensate layer valued at an estimated price with the price of future receipts
        if any. If the estimated price is equals to the real price, no layer is created but
        the original layer is marked as compensated.

        :param company: recordset of `res.company` to limit the execution of the vacuum
        """
        self.ensure_one()
        currency_rate = self.env['res.currency'].search([('id', '=', self.env.company.stock_currency_id.id)], limit=1).rate
        if company is None:
            company = self.env.company
        svls_to_vacuum = self.env['stock.valuation.layer'].sudo().search([
            ('product_id', '=', self.id),
            ('remaining_qty', '<', 0),
            ('stock_move_id', '!=', False),
            ('company_id', '=', company.id),
        ], order='create_date, id')
        if not svls_to_vacuum:
            return

        as_svls = []

        domain = [
            ('company_id', '=', company.id),
            ('product_id', '=', self.id),
            ('remaining_qty', '>', 0),
            ('create_date', '>=', svls_to_vacuum[0].create_date),
        ]
        all_candidates = self.env['stock.valuation.layer'].sudo().search(domain)

        for svl_to_vacuum in svls_to_vacuum:
            # We don't use search to avoid executing _flush_search and to decrease interaction with DB
            candidates = all_candidates.filtered(
                lambda r: r.create_date > svl_to_vacuum.create_date
                or r.create_date == svl_to_vacuum.create_date
                and r.id > svl_to_vacuum.id
            )
            if not candidates:
                break
            qty_to_take_on_candidates = abs(svl_to_vacuum.remaining_qty)
            qty_taken_on_candidates = 0
            tmp_value = 0
            tmp_usd_value = 0
            for candidate in candidates:
                qty_taken_on_candidate = min(candidate.remaining_qty, qty_to_take_on_candidates)
                qty_taken_on_candidates += qty_taken_on_candidate

                candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
                candidate_usd_unit_cost = candidate.remaining_value_usd / candidate.remaining_qty
                value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                usd_value_taken_on_candidate = qty_taken_on_candidate * candidate_usd_unit_cost
                value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
                new_remaining_value = candidate.remaining_value - value_taken_on_candidate
                new_remaining_usd_value = candidate.remaining_value - usd_value_taken_on_candidate

                candidate_vals = {
                    'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                    'remaining_value': new_remaining_value,
                    'remaining_value_usd': new_remaining_usd_value
                }
                candidate.write(candidate_vals)
                if not (candidate.remaining_qty > 0):
                    all_candidates -= candidate

                qty_to_take_on_candidates -= qty_taken_on_candidate
                tmp_value += value_taken_on_candidate
                tmp_usd_value += usd_value_taken_on_candidate
                if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                    break

            # Get the estimated value we will correct.
            remaining_value_before_vacuum = svl_to_vacuum.unit_cost * qty_taken_on_candidates
            remaining_usd_value_before_vacuum = svl_to_vacuum.unit_price_usd * qty_taken_on_candidates
            new_remaining_qty = svl_to_vacuum.remaining_qty + qty_taken_on_candidates
            corrected_value = remaining_value_before_vacuum - tmp_value
            corrected_usd_value = remaining_usd_value_before_vacuum - tmp_usd_value
            svl_to_vacuum.write({
                'remaining_qty': new_remaining_qty,
            })

            # Don't create a layer or an accounting entry if the corrected value is zero.
            if svl_to_vacuum.currency_id.is_zero(corrected_value):
                continue
            corrected_value = svl_to_vacuum.currency_id.round(corrected_value)
            move = svl_to_vacuum.stock_move_id
            vals = {
                'product_id': self.id,
                'value': corrected_value,
                'inventory_value_usd': corrected_usd_value,
                'unit_price_usd': 0,
                'unit_cost': 0,
                'quantity': 0,
                'remaining_qty': 0,
                'stock_move_id': move.id,
                'company_id': move.company_id.id,
                'description': 'Revaluation of %s (negative inventory)' % move.picking_id.name or move.name,
                'stock_valuation_layer_id': svl_to_vacuum.id,
            }
            vacuum_svl = self.env['stock.valuation.layer'].sudo().create(vals)

            if self.valuation != 'real_time':
                continue
            as_svls.append((vacuum_svl, svl_to_vacuum))

        # If some negative stock were fixed, we need to recompute the standard price.
        product = self.with_company(company.id)
        if product.cost_method == 'average' and not float_is_zero(product.quantity_svl, precision_rounding=self.uom_id.rounding):
            product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl, 'standard_price_currency': (product.value_svl / product.quantity_svl) * currency_rate})

        self.env['stock.valuation.layer'].browse(x[0].id for x in as_svls)._validate_accounting_entries()

        for vacuum_svl, svl_to_vacuum in as_svls:
            self._create_fifo_vacuum_anglo_saxon_expense_entry(vacuum_svl, svl_to_vacuum)
        #vacuum_svl.stock_move_id._account_entry_move(vacuum_svl.quantity, vacuum_svl.description, vacuum_svl.id, vacuum_svl.value,vacuum_svl.remaining_value_usd)

    def compute_average_cost(self):
        for rec in self:
            if rec.cost_method in ('average', 'fifo'):
                average_cost = 0.0
                rec.cost_price_usd = 0
                # quant_ids = self.env['stock.valuation.layer'].search([('product_id', '=', rec.id),
                #                                                       ('quantity', '>', 0.0)])
                quant_ids = self.env['stock.valuation.layer'].search([('product_id', '=', rec.id)])
                total_cost = sum(quant_ids.mapped('inventory_value_usd'))
                total_qty = sum(quant_ids.mapped('quantity'))
                count= len(quant_ids)
                if total_qty > 0.0:
                    average_cost = total_cost / total_qty
                    rec.cost_price_usd = average_cost
            else:
                rec.cost_price_usd = rec.standard_price * self.env['res.currency'].search(
                    [('id', '=', self.env.company.stock_currency_id.id)], limit=1).rate

    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'company')
    def _compute_value_svl(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        domain = [
            ('product_id', 'in', self.ids),
            ('company_id', '=', company_id.id),
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain.append(('create_date', '<=', to_date))
        groups = self.env['stock.valuation.layer']._read_group(domain, ['value:sum', 'quantity:sum', 'inventory_value_usd:sum'], ['product_id'])
        products = self.browse()
        for group in groups:
            product = self.browse(group['product_id'][0])
            value_svl = company_id.currency_id.round(group['value'])
            avg_cost = value_svl / group['quantity'] if group['quantity'] else 0
            product.value_svl = value_svl
            product.currency_value_svl = self.env.company.stock_currency_id.round(group['inventory_value_usd'])
            product.quantity_svl = group['quantity']
            product.avg_cost = avg_cost
            product.total_value = avg_cost * product.sudo(False).qty_available
            products |= product
        remaining = (self - products)
        remaining.value_svl = 0
        remaining.currency_value_svl = 0
        remaining.quantity_svl = 0
        remaining.avg_cost = 0
        remaining.total_value = 0

    def _change_standard_price(self, new_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        # Handle stock valuation layers.

        if self.filtered(lambda p: p.valuation == 'real_time') and not self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
            raise UserError(_("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        svl_vals_list = []
        company_id = self.env.company
        for product in self:
            if product.cost_method not in ('standard', 'average'):
                continue
            quantity_svl = product.sudo().quantity_svl
            if float_compare(quantity_svl, 0.0, precision_rounding=product.uom_id.rounding) <= 0:
                continue
            digits = self.env['decimal.precision'].precision_get('Product Price')
            rounded_new_price = float_round(new_price, precision_digits=digits)
            diff = rounded_new_price - product.standard_price
            value = company_id.currency_id.round(quantity_svl * diff)
            if company_id.currency_id.is_zero(value):
                continue

            currency_rate = self.env['res.currency'].search([('id', '=', self.env.company.stock_currency_id.id)], limit=1).rate
            svl_vals = {
                'company_id': company_id.id,
                'product_id': product.id,
                'description': _('Product value manually modified (from %s to %s)') % (product.standard_price, rounded_new_price),
                'value': value,
                'inventory_value_usd': value * currency_rate,
                'quantity': 0,
            }
            svl_vals_list.append(svl_vals)
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

        # Handle account moves.
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self}
        am_vals_list = []
        for stock_valuation_layer in stock_valuation_layers:
            product = stock_valuation_layer.product_id
            value = stock_valuation_layer.value

            if product.valuation != 'real_time' or product.type != 'product':
                continue

            # Sanity check.
            if not product_accounts[product.id].get('expense'):
                raise UserError(_('You must set a counterpart account on your product category.'))
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

            if value < 0:
                debit_account_id = product_accounts[product.id]['expense'].id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id
            else:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['expense'].id

            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': company_id.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [stock_valuation_layer.id])],
                'move_type': 'entry',
                'line_ids': [(0, 0, {
                    'name': _(
                        '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
                        user=self.env.user.name,
                        previous=product.standard_price,
                        new_price=new_price,
                        product=product.display_name
                    ),
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                }), (0, 0, {
                    'name': _(
                        '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
                        user=self.env.user.name,
                        previous=product.standard_price,
                        new_price=new_price,
                        product=product.display_name
                    ),
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'product_id': product.id,
                })],
            }
            am_vals_list.append(move_vals)

        account_moves = self.env['account.move'].sudo().create(am_vals_list)
        if account_moves:
            account_moves._post()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product'),
    ], string='Product Type', default='product', required=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A consumable product is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.')
