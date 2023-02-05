##############################################################################
#    Description: Accounting Approval                                        #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.tools import image_process
from odoo.exceptions import Warning, ValidationError, UserError


#################################################################################################
# inherit
class CheckFollowups(models.Model):
    _inherit = 'check_followups.check_followups'

    @api.depends('payment_id', 'finance_id')
    def _compute_partners(self):
        for r in self:
            if r.payment_id:
                if r.payment_id and r.payment_id.payment_type == 'inbound':
                    r.beneficiary_id = r.payment_id.company_id.partner_id or False
                    r.account_holder = r.payment_id.partner_id or False
                elif r.payment_id and r.payment_id.payment_type == 'outbound':
                    r.beneficiary_id = r.payment_id.partner_id or False
                    r.account_holder = r.payment_id.company_id.partner_id or False
                elif r.payment_id and r.payment_id.payment_type == 'transfer':
                    r.beneficiary_id = r.account_holder = r.payment_id.company_id.partner_id or False
            elif r.finance_id:
                r.account_holder = r.finance_id.company_id.partner_id.id
                if r.finance_id.partner_id:
                    r.beneficiary_id = r.finance_id.partner_id.id
                else:
                    r.beneficiary_id = r.finance_id.user_id.partner_id.id
                r.account_holder = r.finance_id.company_id.partner_id.id

    finance_line_id = fields.Many2one('finance.approval.check.line', string='Finance Approval', ondelete="cascade")
    finance_id = fields.Many2one('finance.approval', string='Finance Approval', ondelete="cascade")
    approval_check = fields.Boolean('Approval Check')
    account_holder = fields.Many2one('res.partner', string='Account Holder', readonly=True, compute=_compute_partners)
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary', readonly=True, compute=_compute_partners)

    def make_move(self):
        res = super(CheckFollowups, self).make_move()
        if self.approval_check == True:
            today_date = fields.Date.today()
            aml = self.env['account.move.line']
            debit, credit, ss, amount_currency = aml.with_context(date=self.finance_id.fa_date).compute_amount_fields(
                self.amount, self.finance_id.request_currency, self.finance_id.company_id.currency_id)
            move = self.env['account.move'].create(self._get_move_vals(today_date))

            debit_account_id, credit_account_id = self._get_move_line_accounts()
            amount = self.finance_id.request_amount
            lines = []
            currency_id = False
            if amount_currency:
                currency_id = self.finance_id.request_currency.id
            lines.append((0, 0, self._get_move_line_vals(debit, credit, amount, currency_id, debit_account_id)))
            lines.append((0, 0, self._get_move_line_vals(credit, debit, amount, currency_id, credit_account_id)))
            move.write({'line_ids': lines})
            move.action_post()
            last_state_label = dict(self.fields_get(allfields=['state'])['state']['selection'])[self.Last_state]
            state_label = dict(self.fields_get(allfields=['state'])['state']['selection'])[self.state]
            description = "Check converted from " + last_state_label + " To " + state_label

            self.WriteLog(move.id, description, str(today_date))
        return res

    def action_returnv(self):
        if self.approval_check == True:
            raise UserError(_("You can only return Customer/Vendor Checks!"))
        else:
            self.Last_state = self.state
            self.write({'state': 'return_acv'})
            self.make_move()
        return True

    def _get_move_line_accounts(self):
        res = super(CheckFollowups, self)._get_move_line_accounts()
        if self.approval_check == True:
            if self.finance_id and self.type == 'outbound':
                if self.state == 'withdrawal' and self.Last_state == 'out_standing':
                    return self.finance_line_id.journal_id.company_id.account_journal_payment_credit_account_id.id, self.finance_line_id.journal_id.default_account_id.id
                elif self.state == 'rdv' and self.Last_state == 'out_standing':
                    return self.finance_line_id.journal_id.company_id.account_journal_payment_credit_account_id.id, self.finance_line_id.journal_id.rdv.id
                elif self.state == 'rdv' and self.Last_state == 'withdrawal':
                    return self.finance_line_id.journal_id.default_account_id.id, self.finance_line_id.journal_id.rdv.id
                elif self.state == 'withdrawal' and self.Last_state == 'rdv':
                    return self.finance_line_id.journal_id.rdv.id, self.finance_line_id.journal_id.default_account_id.id
                elif self.state == 'return_acv' and self.Last_state == 'rdv':
                    return self.finance_line_id.journal_id.rdv.id, self.finance_line_id.partner_id.property_account_payable_id.id
                elif self.state == 'return_acv' and self.Last_state == 'out_standing':
                    return self.finance_line_id.journal_id.company_id.account_journal_payment_credit_account_id.id, self.finance_line_id.partner_id.property_account_payable_id.id
                else:
                    _logger.error('can not determine move accounts for {} with state = {}, Last_state = {}. this is unknown change in the state!'.format(self, self.state, self.Last_state))
                    raise ValidationError("Unknown check state changes!\nFrom '{}' to '{}'".format(
                        self.Last_state or '', self.state or ''
                    ))
        return res

    def _get_move_vals(self, move_date):
        res = super(CheckFollowups, self)._get_move_vals(move_date)
        if self.finance_line_id:
            return {
                'date': move_date,
                'ref': self.name,
                'company_id': self.finance_id.company_id.id,
                'journal_id': self.finance_line_id.journal_id.id,
            }
        return res


#################################################################################################
# inherit
class CheckLogs(models.Model):
    _inherit = 'check_followups.checklogs'

    finance_id = fields.Many2one('finance.approval', string='Finance Approval', ondelete="cascade")
