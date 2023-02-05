# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountStatementReport(models.TransientModel):
    _name = 'payment.check_reports'

    @api.model
    def _get_check_number(self):
        return self.env['check_followups.check_followups'].browse(self._context['active_id']).check_no

    @api.model
    def _get_check_name(self):
        return self.env['check_followups.check_followups'].browse(self._context['active_id']).beneficiary_id.name

    # @api.model
    # def _get_amount(self):
    #     return self.env['check_followups.check_followups'].browse(self._context['active_id']).amount

    check_no = fields.Integer("Check No", required=True, default=_get_check_number)
    reprint_flag = fields.Boolean(default=False)
    Account_Holder_Name = fields.Char(default=_get_check_name)
    # amount = fields.Float(default=_get_amount)
    Amount_in_word = fields.Char(compute='_get_amount_in_text')
    amount_lang = fields.Selection([('Ar', 'Arabic'), ('En', 'English')], string='Amount Language', default='Ar')

    @api.depends('amount_lang')
    def _get_amount_in_text(self):
        from ..models.money_to_text_ar import amount_to_text_arabic
        if self.amount_lang == 'Ar':
            self.Amount_in_word = amount_to_text_arabic(
                self.env['check_followups.check_followups'].browse(self._context['active_id']).amount,
                self.env['check_followups.check_followups'].browse(self._context['active_id']).currency_id.name)
        else:
            from ..models.money_to_text_en import amount_to_text
            self.Amount_in_word = amount_to_text(self.env['check_followups.check_followups'].browse(self._context['active_id']).amount,
                                                 self.env['check_followups.check_followups'].browse(
                                                     self._context['active_id']).currency_id.name)




    # def get_defaults(self):
    #     self.Account_Holder_Name = get_check_number
    #     self.
    # }

    def print_check_write(self):
        return self.print_()

    def print_(self):

        # if not self.reprint_flag:
        rec = self.env['check_followups.check_followups'].browse(self._context['active_id'])
        rec.check_no = self.check_no
        # rec.journal_id.sudo().write({'Check_no': self.check_no})
        self.reprint_flag = True
        # rec.state = 'sent'

        data ={
            'id': self._context['active_id'],
            'Name': self.Account_Holder_Name,
            'Amount_in_text': self.Amount_in_word
        }
        return self.env.ref('ii_check_management_15.check_print').report_action(self,data=data)
