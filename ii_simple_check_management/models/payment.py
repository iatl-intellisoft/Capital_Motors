# -*- coding: utf-8 -*-

from odoo import models, fields, api , _
from odoo.exceptions import AccessError, UserError, AccessDenied
from datetime import datetime


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['check_followup'] = {'mode': 'multi', 'domain': [('type', '=', 'bank')]}
        return res


class MoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def compute_amount_fields(self, amount, src_currency, company_currency, invoice_currency=False):
        """ Method kept for compatibility reason """
        return self._compute_amount_fields(amount, src_currency, company_currency)

    @api.model
    def _compute_amount_fields(self, amount, src_currency, company_currency):
        """ Helper function to compute value for fields debit/credit/amount_currency based on an amount and the currencies given in parameter"""
        amount_currency = False
        currency_id = False
        if src_currency and src_currency != company_currency:
            amount_currency = amount
            amount = src_currency.with_context(self._context).compute(amount, company_currency)
            currency_id = src_currency.id
        debit = amount > 0 and amount or 0.0
        credit = amount < 0 and -amount or 0.0
        return debit, credit, amount_currency, currency_id


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    #check_type = fields.Selection([('direct', 'Direct'), ('indirect', 'indirecting')], 'Check type', default='direct')
    check_type = fields.Selection([('direct', 'Direct'), ('indirect', 'PDC')], string="Check Type",
                                  default='direct')
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method')
    payment_method_code = fields.Char(related='payment_method_id.code')
    return_check_move_id = fields.Many2one('account.move', 'Check clearance move', readonly=True)
    clearance_date = fields.Date('Check Clearance Date')
    ####################################################
    # check_line_ids = fields.One2many('account.payment.check.line', 'payment_id', 'Check(s)')
    check_ids = fields.One2many('check_followups.check_followups', 'payment_id', 'Check(s)')
    partner_bank_account = fields.Many2one('partner.bank.account', 'Partner Account', store=False)
    Account_No = fields.Char(string='Account No')
    Check_no = fields.Char('Check No')
    Bank_id = fields.Char(string='Partner Bank')
    check_date = fields.Date('Check Date')
    check_amount_in_words = fields.Char('Amount In Words')

    # Modify indirecting account to be direct
    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        if self.check_type != 'indirect' or not self.check_type:
            res[0].update({'account_id':self.journal_id.default_account_id.id})
        return res

    # Modify move when check_type change
    def _synchronize_to_moves(self, changed_fields):
        for rec in self:
            res = super(AccountPayment,self)
            res._synchronize_to_moves(changed_fields)
            if any(field_name in changed_fields for field_name in (
                    'check_type','payment_method_id')):
                for pay in res.with_context(skip_account_move_synchronization=True):
                    liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
                    line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=None)
                    line_ids_commands = [(1, liquidity_lines.id, line_vals_list[0])]
                    pay.move_id.write({
                        'line_ids': line_ids_commands,
                    })
        return res

    ######################################
    @api.onchange('amount', 'currency_id')
    def _compute_amount_in_words(self):
        from . import money_to_text_ar
        for r in self:
            r.check_amount_in_words = money_to_text_ar.amount_to_text_arabic(r.amount, r.currency_id.name)

    @api.returns('check_followups.check_followups')
    def _create_check(self):
        self.ensure_one()
        for rec in self:
            # if self.payment_type == 'outbound':
            check_dict = {
                'payment_id': rec.id,
                'type': rec.payment_type,
                'amount': rec.amount,
                'Date': rec.check_date,
                'bank_id': False,
                'partner_bank': rec.Bank_id,
                #'check_no': rec.Check_no,
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
            inbound_check = r.env.ref('ii_simple_check_management.account_payment_method_check_in')
            outbound_check = r.env.ref('ii_simple_check_management.account_payment_method_check_out')



            if r.payment_method_id in [inbound_check, outbound_check]:
                if not r._context.get('check_payment', False):
                    # no check_payment means this payment is the first payment for the check, and it is not a returning
                    # payment (returning an already existing check to customer or to us)
                    payment_context = {
                        'check_payment': True,
                        'check_last_state': False,
                    }
                    if r.payment_method_id == inbound_check:
                        payment_context.update(dict(check_state='under_collection'))
                    elif r.payment_method_id == outbound_check:
                        r.journal_id.sudo().Check_no = r.Check_no
                        payment_context.update(dict(check_state='out_standing'))

                    r = r.with_context(payment_context)
                    super(AccountPayment, r).action_post()
                    if r.check_type == 'indirect':
                        check = r._create_check()
                        for line in r.move_id.line_ids:
                            if not line.ref:
                                line.ref = check.name
                    #return
            else:
                super(AccountPayment, r).action_post()


    # Modify indirecting account to be direct
    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        if self.check_type != 'indirect' or not self.check_type:
            res[0].update({'account_id':self.journal_id.default_account_id.id})
        return res

    def action_cancel(self):
        for record in self:
            super(AccountPayment, record).action_cancel()
            if record.check_ids:
                if record.check_ids.filtered(lambda check: check.state not in ('out_standing','rdv','under_collection','rdc','cancel')):
                    raise UserError(_("Payment Cannot be cancelled, check should be either unused or rejected"))
                else:
                    record.check_ids.state = 'cancel'

    def action_draft(self):
        for record in self:
            super(AccountPayment, record).action_draft()
            if record.check_ids:
                if record.check_ids.filtered(lambda check: check.state not in ('out_standing','rdv','under_collection','rdc','cancel')):
                    raise UserError(_("Payment Cannot be rest, check should be either unused or rejected"))
                else:
                    record.check_ids.state = 'cancel'

    def action_view_checks(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        if self.payment_type == 'inbound':
            action = self.env.ref(
                'ii_simple_check_management.check_followups_customer').read()[0]
        elif self.payment_type == 'outbound':
            action = self.env.ref(
                'ii_simple_check_management.check_followups_vendor').read()[0]
        # action = self.env.ref('is_pm_az.action_contract_qty_work').read()[0]

        checks = self.mapped('check_ids')
        if len(checks) > 1:
            action['domain'] = [('id', 'in', checks.ids)]
        elif checks:
            if self.payment_type == 'inbound':
                action['views'] = [(self.env.ref('ii_simple_check_management.check_followups_customerformview').id, 'form')]
            elif self.payment_type == 'outbound':
                result = self.env.ref(
                    'ii_simple_check_management.check_followups_form')
                action['views'] = [(self.env.ref('ii_simple_check_management.check_followups_form').id, 'form')]
            # action['views'] = [(self.env.ref('is_pm_az.contract_qty_work_view').id, 'form')]
            action['res_id'] = checks.id
        return action


class account_payment_register(models.TransientModel):
    _inherit = 'account.payment.register'

    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method')
    payment_method_code = fields.Char(related='payment_method_id.code')
    check_type = fields.Selection([('direct', 'Direct'), ('indirect', 'PDC')], string="Check Type",
                                  default='direct')
    clearance_date = fields.Date('Check Date')
    check_no = fields.Char('Check No.')

    def _create_payment_vals_from_wizard(self,batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals.update(
            {
                'check_type': self.check_type,
                'clearance_date': self.clearance_date,
            }
        )
        return payment_vals
