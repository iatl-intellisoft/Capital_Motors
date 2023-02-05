# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################
from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.addons.stock_landed_costs.models import product
from odoo.exceptions import UserError


class stock_landed_cost(models.Model):
    _inherit = 'stock.landed.cost'

    # def get_valuation_lines(self):
    #     self.ensure_one()
    #     lines = []

    #     for move in self._get_targeted_move_ids():
    #         # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
    #         if move.product_id.valuation != 'real_time' or move.product_id.cost_method not in ['average', 'fifo']:
    #             continue
    #         vals = {
    #             'product_id': move.product_id.id,
    #             'move_id': move.id,
    #             'quantity': move.product_qty,
    #             'former_cost': sum(move.stock_valuation_layer_ids.mapped('value')),
    #             'weight': move.product_id.weight * move.product_qty,
    #             'volume': move.product_id.volume * move.product_qty
    #         }
    #         lines.append(vals)

    #     if not lines:
    #         target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
    #         raise UserError(_("You cannot apply landed costs on the chosen %s(s). Landed costs can only be applied for products with FIFO or average costing method.", target_model_descriptions[self.target_model]))
    #     return lines

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
                if line.product_id.categ_id.property_cost_method == 'average' and line.product_id.qty_available > 0:
                    adjust_value = line.additional_landed_cost 
                    qty_available = line.product_id.qty_available
                    standard_price = line.product_id.standard_price
                    pro_price = (adjust_value + (qty_available * standard_price)) / qty_available
                    line.product_id.write({'standard_price':pro_price})
                remaining_qty = sum(line.move_id.stock_valuation_layer_ids.mapped('remaining_qty'))
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]

                # Prorate the value at what's still in stock
                cost_to_add = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost
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
                    })
                    linked_layer.remaining_value += cost_to_add
                    valuation_layer_ids.append(valuation_layer.id)
                # Update the AVCO
                product = line.move_id.product_id
                if product.cost_method == 'average':
                    cost_to_add_byproduct[product] += cost_to_add
                # Products with manual inventory valuation are ignored because they do not need to create journal entries.
                if product.valuation != "real_time":
                    continue
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

#    @api.multi
#    def button_validate(self):
#        if any(cost.state != 'draft' for cost in self):
#            raise UserError(_('Only draft landed costs can be validated'))
#        if any(not cost.valuation_adjustment_lines for cost in self):
#            raise UserError(_('No valuation adjustments lines. You should maybe recompute the landed costs.'))
#        if not self._check_sum():
#            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

#        for cost in self:
#            move = self.env['account.move'].create({
#                'journal_id': cost.account_journal_id.id,
#                'date': cost.date,
#                'ref': cost.name
#            })
#            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
#                per_unit = line.final_cost / line.quantity
#                diff = per_unit - line.former_cost_per_unit
#                if line.product_id.categ_id.property_cost_method == 'average':
#                    adjust_value = line.additional_landed_cost
#                    qty_available = line.product_id.qty_available
#                    standard_price = line.product_id.standard_price
#                    pro_price = (adjust_value + (qty_available * standard_price)) / qty_available
#                    line.product_id.write({'standard_price':pro_price})

#                # If the precision required for the variable diff is larger than the accounting
#                # precision, inconsistencies between the stock valuation and the accounting entries
#                # may arise.
#                # For example, a landed cost of 15 divided in 13 units. If the products leave the
#                # stock one unit at a time, the amount related to the landed cost will correspond to
#                # round(15/13, 2)*13 = 14.95. To avoid this case, we split the quant in 12 + 1, then
#                # record the difference on the new quant.
#                # We need to make sure to able to extract at least one unit of the product. There is
#                # an arbitrary minimum quantity set to 2.0 from which we consider we can extract a
#                # unit and adapt the cost.
#                curr_rounding = line.move_id.company_id.currency_id.rounding
#                diff_rounded = tools.float_round(diff, precision_rounding=curr_rounding)
#                diff_correct = diff_rounded
#                quants = line.move_id.quant_ids.sorted(key=lambda r: r.qty, reverse=True)
#                quant_correct = False
#                if quants\
#                        and tools.float_compare(quants[0].product_id.uom_id.rounding, 1.0, precision_digits=1) == 0\
#                        and tools.float_compare(line.quantity * diff, line.quantity * diff_rounded, precision_rounding=curr_rounding) != 0\
#                        and tools.float_compare(quants[0].qty, 2.0, precision_rounding=quants[0].product_id.uom_id.rounding) >= 0:
#                    # Search for existing quant of quantity = 1.0 to avoid creating a new one
#                    quant_correct = quants.filtered(lambda r: tools.float_compare(r.qty, 1.0, precision_rounding=quants[0].product_id.uom_id.rounding) == 0)
#                    if not quant_correct:
#                        quant_correct = quants[0]._quant_split(quants[0].qty - 1.0)
#                    else:
#                        quant_correct = quant_correct[0]
#                        quants = quants - quant_correct
#                    diff_correct += (line.quantity * diff) - (line.quantity * diff_rounded)
#                    diff = diff_rounded

#                quant_dict = {}
#                for quant in quants:
#                    quant_dict[quant] = quant.cost + diff
#                if quant_correct:
#                    quant_dict[quant_correct] = quant_correct.cost + diff_correct
#                for quant, value in quant_dict.items():
#                    quant.sudo().write({'cost': value})
#                qty_out = 0
#                for quant in line.move_id.quant_ids:
#                    if quant.location_id.usage != 'internal':
#                        qty_out += quant.qty
#                line._create_accounting_entries(move, qty_out)
#            move.assert_balanced()
#            cost.write({'state': 'done', 'account_move_id': move.id})
#            move.post()
#        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
