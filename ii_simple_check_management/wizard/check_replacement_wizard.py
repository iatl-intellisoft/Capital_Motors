# -*- coding: utf-8 -*-
from odoo   import fields, models, api
from odoo.exceptions import UserError, ValidationError


class CheckReplacement(models.TransientModel):
    _name = 'check.replacement'

    def _default_amount(self):
        return self._context.get('_default_amount', 0)

    amount = fields.Monetary("Amount", required=True, default=_default_amount)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    date = fields.Date(string='Check Date', required=True)
    number = fields.Integer("Check Number", required=True)
    memo = fields.Char(string='Memo')
    wizard_id = fields.Many2one('check.replacement.wizard')

    def _default_account_number(self):
        return self._context.get('_default_account_number', 0)

    def _default_bank_id(self):
        return self._context.get('_default_bank_id', False)

    account_number = fields.Char(string='Account Number', default=_default_account_number)
    bank_id = fields.Many2one('res.bank', string='Bank', default=_default_bank_id)

    @api.constrains('journal_id')
    def _validate_journal_id(self):
        #inbound_check = self.env.ref('ii_simple_check_management.account_payment_method_check_inBound')
        inbound_check = self.env.ref('check_printing_custom.account_payment_method_check_inbound')

        for r in self:
            if inbound_check not in r.journal_id.inbound_payment_method_ids:
                raise ValidationError('"{}" journal does not allow check payments!'.format(r.journal_id.name))


class CashReplacement(models.TransientModel):
    _name = 'cash.replacement'

    def _default_amount(self):
        return self._context.get('_default_amount', 0)

    amount = fields.Monetary("Amount", required=True, default=_default_amount)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    date = fields.Date(string='Date', required=True, default=lambda self: fields.Date.today())
    memo = fields.Char(string='Memo')
    wizard_id = fields.Many2one('check.replacement.wizard')


class PaymentReplacementWizard(models.TransientModel):
    _name = 'check.replacement.wizard'

    def _default_original_check(self):
        return self.env['check_followups.check_followups'].browse([self._context.get('_default_original_check', None)])

    original_check = fields.Many2one('check_followups.check_followups', default=_default_original_check)
    original_amount = fields.Monetary(related='original_check.amount', readonly=True)
    currency_id = fields.Many2one(related='original_check.currency_id', readonly=True)
    account_number = fields.Char(string='Account Number', related='original_check.payment_id.Account_No', readonly=True)
    bank_id = fields.Char(string='Bank', related='original_check.payment_id.Bank_id', readonly=True)

    check_replacement_ids = fields.One2many('check.replacement', 'wizard_id')
    cash_replacement_ids = fields.One2many('cash.replacement', 'wizard_id')
    returning_memo = fields.Char(string='Memo (Return to AC payment)', required=True)

    def confirm(self):
        check = self.env['check_followups.check_followups'].browse(self._context['active_id'])
        if check.state not in ['under_collection', 'rdc']:
            raise UserError('Check is not under collection nor RD.')
        self._validate_amount()

        self.add_check_replacements(check)
        self.add_cash_replacements(check)
        check.action_returnc(self.returning_memo)

    def add_check_replacements(self, check):
        today = fields.date.today()
        for check_line in self.check_replacement_ids:
            payment_dict = {
                'amount': check_line.amount,
                'journal_id': check_line.journal_id.id,
                'currency_id': check_line.currency_id.id,
                'check_date': check_line.date,
                'Account_No': check_line.account_number,
                'Bank_id': check_line.bank_id.id,
                'Check_no': check_line.number,
                'communication': check_line.memo,
                'payment_date': today,
                'parent_id': check.payment_id.id,
            }

            check.payment_id.copy(payment_dict).post()

    def add_cash_replacements(self, check):
        inbound_manual = self.env.ref('account.account_payment_method_manual_in')
        for cash_line in self.cash_replacement_ids:
            payment_dict = {
                'amount': cash_line.amount,
                'journal_id': cash_line.journal_id.id,
                'currency_id': cash_line.currency_id.id,

                'payment_date': cash_line.date,
                'communication': cash_line.memo,

                'payment_method_id': inbound_manual.id,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': check.account_holder.id,

                'parent_id': check.payment_id.id,
            }
            self.env['account.payment'].create(payment_dict).post()

    def _validate_amount(self):
        total_amount = sum(self.check_replacement_ids.mapped('amount')) + sum(self.cash_replacement_ids.mapped('amount'))
        if total_amount != self.original_check.amount:
            raise ValidationError('Total amount of replacement payments ({}) is {} than the check ({}).'.
                                  format(total_amount, total_amount < self.original_check.amount and 'less' or 'greater'
                                         , self.original_check.amount))

