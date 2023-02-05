# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


# class SaleOrderLine(models.Model):
    # _inherit = 'sale.order.line'

    # @api.constrains('price_unit')
    # def _check_sale_price(self):
    #     print((self.product_id.az_margin / 100*self.purchase_price) ,"jkhgggggggggggggggggggggggg",(self.product_id.az_margin / 100*self.purchase_price) + (self.purchase_price),self.purchase_price)
    #     if self.price_unit <= (self.product_id.az_margin / 100*self.purchase_price) + (self.purchase_price):
    #         print("jfdffffffffffffff")
    #         raise ValidationError(_('Sale Price must Be Greater '))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def confirm_appro_draf(self):
        invoices = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id), ('state', '=', 'posted')])
        total = 0.0
        for invoice in invoices:
            if invoice:
                total += invoice.amount_residual
        if total >= self.partner_id.credit_limit and self.partner_id.credit_limit > 0:
            raise UserError(_(
                'This Customer has exceed his Credit Limit '
            ))
        for line in self.order_line:
            if line.discount > 0.0:
                self.state = 'first_approve'
                break
            else:
                self.state = 'draft'

    def appro_sent_approved(self):
        if self.state == 'first_approve':
            self.state = 'approved'

    def approved_Quatatin(self):
        if self.state == 'approved':
            self.state = 'draft'

    # def action_confirm(self):
    #     if self._get_forbidden_state_confirm() & set(self.mapped('state')):
    #         raise UserError(_(
    #             'It is not allowed to confirm an order in the following states: %s'
    #         ) % (', '.join(self._get_forbidden_state_confirm())))

    #     for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
    #         order.message_subscribe([order.partner_id.id])
    #     self.write({
    #         'state': 'sale',
    #         'date_order': fields.Datetime.now()
    #     })
    #     self._action_confirm()
    #     if self.env.user.has_group('sale.group_auto_done_setting'):
    #         self.action_done()
    #     return True

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('confirm', 'Confirm'),
        ('first_approve', 'First Approval'),
        ('approved', 'Second Approval'),
        ('sent', 'Quotation Sent'),
        ('approved', 'Second Approval'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True,
                       states={'confirm': [('readonly', False)], 'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'confirm': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [(
            'readonly', False)], 'sent_approve': [('readonly', False)], 'approved': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address',
        readonly=True, required=True,
        states={'confirm': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [
            ('readonly', False)], 'sent_approve': [('readonly', False)], 'approved': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', readonly=True, required=True,
        states={'confirm': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [
            ('readonly', False)], 'sent_approve': [('readonly', False)], 'approved': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )

    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        required=True, readonly=True, states={'confirm': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sent_approve': [('readonly', False)], 'approved': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If you change the pricelist, only newly added lines will be affected.")

    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account',
        readonly=True, copy=False, check_company=True,  # Unrequired company
        states={'confirm': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [(
            'readonly', False)], 'sent_approve': [('readonly', False)], 'approved': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="The analytic account related to a sales order.")

    validity_date = fields.Date(string='Expiration', readonly=True, copy=False,
                                states={'confirm': [('readonly', False)], 'draft': [
                                    ('readonly', False)], 'sent': [('readonly', False)]},
                                )
    sale_order_template_id = fields.Many2one(
        'sale.order.template', 'Quotation Template',
        readonly=True, check_company=True,
        states={'confirm': [('readonly', False)], 'draft': [
            ('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    date_order = fields.Datetime(string='Order Date', required=True,  index=True, states={'confirm': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [
                                 ('readonly', False)]}, copy=False, default=fields.Datetime.now, help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.")


class res_partner(models.Model):
    _inherit = 'res.partner'

    credit_limit = fields.Float(string='Credit Limit')
    funding_entity = fields.One2many(
        'funding.entity', 'entry_id', string='Funding Entity')


class Funding_Entity(models.Model):
    _name = 'funding.entity'
    _description = 'Funding Entity'

    name = fields.Many2one('funding', string='Name')
    code = fields.Char(string='Code')
    payment_term = fields.Char(string='Payment Term')
    entry_id = fields.Many2one("res.partner", "entry_id", ondelete="cascade")


class Funding(models.Model):
    _name = 'funding'
    _description = 'Funding'

    name = fields.Char("Name")
