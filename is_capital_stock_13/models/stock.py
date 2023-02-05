##############################################################################
#    Description: Stock Customization                                   #
#    Author: IntelliSoft Software                                            #
#    Date: december 2020 -  Till Now                                              #
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WizardStockValuation(models.Model):
    _name = 'wizard.stock.valuation'
    _description = 'Stock Valuation Wizard'

    def compute_update_usd(self):
        currency_rate = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.env.ref('base.USD').id)], limit=1, order='name desc').company_rate
        move = {}
        # inverse_company_rate
        if currency_rate != 0.0:
            for categ in self.env['product.category'].search([('property_valuation', '=', 'real_time')]):
                new_remaining_total = 0.0
                old_remaining = 0.0
                adjust_amount = 0.0
                lines = []
                layer = self.env['stock.valuation.layer'].sudo().search(
                    [('product_id.categ_id', '=', categ.id), ('quantity', '>', 0.0), ('remaining_qty', '>', 0)])
                if layer:
                    old_remaining = sum(layer.mapped('remaining_value'))
                    remaining_qty = sum(layer.mapped('remaining_qty'))
                    for rec in layer:
                        new_unit_cost = rec.unit_price_usd / currency_rate
                        new_value = (rec.unit_price_usd *
                                     rec.quantity) / currency_rate
                        new_remaining_value = (
                            rec.unit_price_usd * rec.remaining_qty) / currency_rate
                        new_remaining_total += new_remaining_value
                        rec.update(
                            {'unit_cost': new_unit_cost, 'value': new_value, 'remaining_value': new_remaining_value})
                    if layer[-1].product_id.cost_method == 'average':
                        layer[-1].product_id.standard_price = new_remaining_total / \
                            remaining_qty
                    adjust_amount = new_remaining_total - old_remaining
                    adjust_amount = round(adjust_amount, 2)
                    # raise UserError(adjust_amount)

                if adjust_amount > 0.0:
                    debit_line = (0, 0, {
                        'account_id': categ.property_stock_valuation_account_id.id,
                        'name': 'Category ' + categ.name + ' Inventory Adjustment at' + str(fields.Date.today()),
                        'debit': adjust_amount,
                        'credit': 0.0,
                    })
                    lines.append(debit_line)
                    credit_line = (0, 0, {
                        'account_id': categ.inventory_adjustment.id,
                        'name': 'Category ' + categ.name + ' Inventory Adjustment at' + str(fields.Date.today()),
                        'credit': adjust_amount,
                        'debit': 0.0
                    })
                    lines.append(credit_line)
                if adjust_amount < 0.0:
                    debit_line = (0, 0, {
                        'account_id': categ.property_stock_valuation_account_id.id,
                        'name': 'Category ' + categ.name + ' Inventory Adjustment at' + str(fields.Date.today()),
                        'credit': -adjust_amount,
                        'debit': 0.0,
                    })
                    lines.append(debit_line)
                    credit_line = (0, 0, {
                        'account_id': categ.inventory_adjustment.id,
                        'name': 'Category ' + categ.name + ' Inventory Adjustment at' + str(fields.Date.today()),
                        'debit': -adjust_amount,
                        'credit': 0.0,
                    })
                    lines.append(credit_line)
                if lines:
                    move = {
                        'date': fields.Date.today(),
                        'ref': 'Category ' + categ.name + ' Adjustment at' + str(fields.Date.today()) + 'With USD Rate =' + str(1 / currency_rate),
                        'journal_id': categ.property_stock_journal.id,
                    }
                    move['line_ids'] = lines
                    move_id = self.env['account.move'].create(move)
                    move_id.action_post()


class ProductCategory(models.Model):
    _inherit = 'product.category'

    inventory_adjustment = fields.Many2one(
        'account.account', string='Inventory USD Adjustment')


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    @api.model
    def compute_update_value_usd(self):
        currency_rate = self.env['res.currency'].search(
            [('id', '=', self.env.ref('base.USD').id)], limit=1).rate
        move = {}
        if currency_rate != 0.0:
            for categ in self.env['product.category'].search([('property_valuation', '=', 'real_time')]):
                new_remaining_total = 0.0
                old_remaining = 0.0
                adjust_amount = 0.0
                lines = []
                layer = self.env['stock.valuation.layer'].sudo().search(
                    [('product_id.categ_id', '=', categ.id), ('quantity', '>', 0.0), ('remaining_qty', '>', 0)])
                if layer:
                    old_remaining = sum(layer.mapped('remaining_value'))
                    for rec in layer:
                        new_unit_cost = rec.unit_price_usd / currency_rate
                        new_value = (rec.unit_price_usd *
                                     rec.quantity) / currency_rate
                        new_remaining_value = (
                            rec.unit_price_usd * rec.remaining_qty) / currency_rate
                        new_remaining_total += new_remaining_value
                        rec.update(
                            {'unit_cost': new_unit_cost, 'value': new_value, 'remaining_value': new_remaining_value})
                    adjust_amount = new_remaining_total - old_remaining

                if adjust_amount > 0.0:
                    debit_line = (0, 0, {
                        'account_id': categ.property_stock_valuation_account_id.id,
                        'name': 'Category ' + categ.name + ' Inventory Adjustment at' + str(fields.Date.today()),
                        'debit': adjust_amount,
                        'credit': 0.0,
                    })
                    lines.append(debit_line)
                    credit_line = (0, 0, {
                        'account_id': categ.inventory_adjustment.id,
                        'name': 'Category ' + categ.name + ' Inventory Adjustment at' + str(fields.Date.today()),
                        'credit': adjust_amount,
                        'debit': 0.0
                    })
                    lines.append(credit_line)
                if adjust_amount < 0.0:
                    debit_line = (0, 0, {
                        'account_id': categ.property_stock_valuation_account_id.id,
                        'name': 'Category ' + categ.name + ' Inventory Adjustment at' + str(fields.Date.today()),
                        'credit': adjust_amount,
                        'debit': 0.0,
                    })
                    lines.append(debit_line)
                    credit_line = (0, 0, {
                        'account_id': categ.inventory_adjustment.id,
                        'name': 'Category ' + categ.name + ' Inventory Adjustment at' + str(fields.Date.today()),
                        'debit': adjust_amount,
                        'credit': 0.0,
                    })
                    lines.append(credit_line)
                if lines:
                    move = {
                        'date': fields.Date.today(),
                        'ref': 'Category ' + categ.name + ' Adjustment at' + str(
                            fields.Date.today()) + 'With USD Rate =' + str(1 / currency_rate),
                        'journal_id': categ.property_stock_journal.id,
                    }
                    move['line_ids'] = lines
                    move_id = self.env['account.move'].create(move)
                    move_id.action_post()
