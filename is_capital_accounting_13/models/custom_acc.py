from odoo import models, fields, api, _
# from odoo.exceptions import UserError
# from odoo.tools.float_utils import float_round as round, float_compare
# import datetime
from datetime import date, datetime


class ProductTemplate(models.Model):
    _inherit = "product.template"

    unit_cost_usd = fields.Float("Unit Cost in USD", digits=(
        16, 4), related="product_id.unit_cost_usd")
    product_id = fields.Many2one('product.product')


class ValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    value_usd = fields.Float("USD Value", digits=(16, 4))
    unit_cost_usd = fields.Float("Unit Cost in USD", digits=(16, 4))


class ProductProduct(models.Model):
    _inherit = "product.product"

    unit_cost_usd = fields.Float("Unit Cost in USD", digits=(
        16, 4), compute='compute_unit_cost_usd')

    def compute_unit_cost_usd(self):
        for rec in self:
            # rec.unit_cost_usd = 0.0
            average_usd = 0.0
            valuation_ids = self.env['stock.valuation.layer'].search(
                [('product_id', '=', rec.id)])
            value_usd = sum(valuation_ids.mapped('value_usd'))
            qty = sum(valuation_ids.mapped('quantity'))
            if qty > 0.0:
                average_usd = value_usd / qty
            rec.unit_cost_usd = average_usd

    def _prepare_in_svl_vals(self, quantity, unit_cost):
        """Prepare the values for a stock valuation layer created by a receipt.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :param unit_cost: the unit cost to value `quantity`
        :return: values to use in a call to create
        :rtype: dict
        """
        # datetime.now().date())
        self.ensure_one()
        date = 0
        print(self.unit_cost_usd, 'nosaa')
        for move_id in self.stock_move_ids:
            date = str(move_id.date)
        # parse to datetime object
        d = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        str_date = d.strftime("%m/%d/%Y")
        currency_name = "USD"
        currency_id = self.env['res.currency'].search([('name', '=', 'USD')],
                                                      limit=1)
        currency_rate = self.env['res.currency.rate'].search(
            [('currency_id', '=', currency_id.id), ('name', '>=', str_date)],
            limit=1, order='name desc')
        vals = {
            'product_id': self.id,
            'value': unit_cost * quantity,
            'unit_cost': unit_cost,
            'quantity': quantity,
            'value_usd': unit_cost * quantity * currency_rate.rate,
            # 'unit_cost_usd': unit_cost * currency_rate.rate
        }
        if self.cost_method in ('average', 'fifo'):
            vals['remaining_qty'] = quantity
            vals['remaining_value'] = vals['value']
        return vals
