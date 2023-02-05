# -*- coding: utf-8 -*-

from odoo import models, fields, api , _
from odoo.exceptions import AccessError, UserError, AccessDenied
from datetime import datetime


class Payment(models.Model):
    _inherit = 'account.payment'

    check_type = fields.Selection([('direct', 'Direct'), ('outstand', 'Outstanding')], 'Check type')
    return_check_move_id = fields.Many2one('account.move', 'Check clearance move', readonly=True)
    cleared = fields.Boolean('Check cleared', default=False)
    clearance_date = fields.Date('Check clearance date')
    check_ids = fields.One2many('check_followups.check_followups', 'payment_id', 'Check(s)')
    partner_bank_account = fields.Many2one('partner.bank.account', 'Partner Account', store=False)
    Account_No = fields.Char(string='Account No')
    Check_no = fields.Char('Check No')
    Bank_id = fields.Char(string='PartnerBank')
    check_date = fields.Date('Check Date')
    check_amount_in_words = fields.Char('Amount In Words')

    child_ids = fields.One2many('account.payment', 'parent_id')
    parent_id = fields.Many2one('account.payment', 'Replacement For', copy=False)

    # Modify outstanding account to be direct
    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super(Payment, self)._prepare_move_line_default_vals()
        if self.payment_method_id == self.env.ref('account.account_payment_method_manual_in'):
            res[0].update({'account_id': self.journal_id.default_account_id.id})
        elif self.payment_method_id == self.env.ref('account.account_payment_method_manual_out'):
            res[0].update({'account_id': self.journal_id.default_account_id.id})
        return res

    @api.onchange('amount', 'currency_id')
    def _compute_amount_in_words(self):
        from . import money_to_text_ar
        for r in self:
            r.check_amount_in_words = money_to_text_ar.amount_to_text_arabic(r.amount, r.currency_id.name)

    @api.returns('check_followups.check_followups')
    def _create_check(self):
        self.ensure_one()
        for rec in self:
            check_dict = {
                'payment_id': rec.id,
                'type': rec.payment_type,
                'amount': rec.amount,
                'Date': rec.check_date,
                'bank_id': False,
                'partner_bank': rec.Bank_id,
                'check_no': rec.Check_no,
                'currency_id': rec.currency_id.id,
                'communication': rec.ref,
                'company_id': rec.company_id.id,

            }
            log_args = {
                'Move_id': rec.move_id.id,
                'payment_id': rec.id,
                'date': rec.date,
            }
            if rec.payment_type == 'inbound':
                check_dict.update({
                    'state': 'under_collection',
                })

                log_args.update({
                    'Description': 'Customer Check Creation',
                })
            elif rec.payment_type in ['outbound', 'transfer']:
                check_dict.update({
                    'state': 'out_standing',
                    'bank_id': rec.journal_id.bank_id.id,
                })
                log_args.update({
                    'Description': 'Vendor Check Creation',
                })

            check = self.env['check_followups.check_followups'].create(check_dict)
            rec.payment_reference = check.name
            check.WriteLog(**log_args)
        return check

    def action_post(self):
        for r in self:
            inbound_check = r.env.ref('ii_check_management_15.account_payment_method_check_inBound')
            # outbound_check = r.env.ref('ii_check_management_15.account_payment_method_check_outBound')
            if r.payment_method_id in [inbound_check]:
                if not r._context.get('check_payment', False):
                    # no check_payment means this payment is the first payment for the check, and it is not a returning
                    # payment (returning an already existing check to customer or to us)
                    payment_context = {
                        'check_payment': True,
                        'check_last_state': False,
                    }
                    if r.payment_method_id == inbound_check:
                        payment_context.update(dict(check_state='under_collection'))
                    # elif r.payment_method_id == outbound_check:
                    #     payment_context.update(dict(check_state='out_standing'))

                    r = r.with_context(payment_context)
                    super(Payment, r).action_post()
                    r._create_check()
                    r.ref = str('Check No/ ') + str(r.Check_no)
                    return

            super(Payment, r).action_post()

    def action_draft(self):
        res = super(Payment, self).action_draft()
        for rec in self:
            if rec.check_ids:
                for check in rec.check_ids:
                    if check.type == 'inbound':
                        if check.state == 'donec':
                            raise UserError('You Cannot Delete The Check already done')
                        else:
                            check.state = 'cancelc'
                    elif check.type == 'outbound':
                        if check.state == 'donev':
                            raise UserError('You Cannot Delete The Check already done')
                        else:
                            check.state = 'cancelv'
        return res

    def action_view_checks(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        if self.payment_type == 'inbound':
            action = self.env.ref(
                'ii_check_management_15.check_followups_customer').read()[0]
        elif self.payment_type == 'outbound':
            action = self.env.ref(
                'ii_check_management_15.check_followups_vendor').read()[0]
        checks = self.mapped('check_ids')
        if len(checks) > 1:
            action['domain'] = [('id', 'in', checks.ids)]
        elif checks:
            if self.payment_type == 'inbound':
                action['views'] = [(self.env.ref('ii_check_management_15.check_followups_customerformview').id, 'form')]
            elif self.payment_type == 'outbound':
                result = self.env.ref(
                    'ii_check_management_15.check_followups_form')
                action['views'] = [(self.env.ref('ii_check_management_15.check_followups_form').id, 'form')]
            action['res_id'] = checks.id
        return action
