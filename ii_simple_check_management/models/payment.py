# -*- coding: utf-8 -*-

from odoo import models, fields, api , _
from odoo.exceptions import AccessError, UserError, AccessDenied

class payment(models.Model):
    _inherit = 'account.payment'

    check_type = fields.Selection([('direct','Direct'),('outstand','Outstanding')],'Check type')
    return_check_move_id = fields.Many2one('account.move','Check clearance move', readonly=True)
    cleared = fields.Boolean('Check cleared', compute='clear_check',store=True,default=False)
    clearance_date = fields.Date('Check clearance date')

    # Modify outstanding account to be direct
    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super(payment, self)._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        if self.check_type != 'outstand' or not self.check_type:
            res[0].update({'account_id':self.journal_id.default_account_id.id})
        return res

    # Modify move when check_type change
    def _synchronize_to_moves(self, changed_fields):
        for rec in self:
            res = super(payment,self)
            res._synchronize_to_moves(changed_fields)
            if  any(field_name in changed_fields for field_name in (
                    'check_type','payment_method_id')):
                for pay in res.with_context(skip_account_move_synchronization=True):
                    liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
                    line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=None)
                    line_ids_commands = [(1, liquidity_lines.id, line_vals_list[0])]
                    pay.move_id.write({
                        'line_ids': line_ids_commands,
                    })
        return res

    def clear_check(self):
        for rec in self:
            rec.cleared=False
            if rec.payment_method_code == 'check_printing' and rec.check_type=='outstand':
                move_obj = self.env['account.move']
                if self.payment_type == 'inbound':
                    # Receive money.
                    counterpart_amount = -self.amount
                elif self.payment_type == 'outbound':
                    # Send money.
                    counterpart_amount = self.amount
                else:
                    counterpart_amount = 0.0
                balance = self.currency_id._convert(counterpart_amount, self.company_id.currency_id, self.company_id,self.date)
                line_ids=[]
                debit_vals = {
                        'name': rec.name+'Check clearance',
                        'date_maturity': rec.clearance_date,
                        'amount_currency': -rec.amount,
                        'currency_id': rec.currency_id.id,
                        'debit':  balance < 0.0 and -balance or balance,
                        'credit':  0.0,
                        'partner_id': rec.partner_id.id,
                        'account_id': rec.journal_id.default_account_id.id if balance < 0.0 else rec.journal_id.payment_credit_account_id.id,
                    }
                line_ids.append((0, 0, debit_vals))
                credit_vals= {
                    'name': rec.name+'Check clearance',
                    'date_maturity': rec.clearance_date,
                    'amount_currency': rec.amount if rec.currency_id else 0.0,
                    'currency_id': rec.currency_id.id,
                    'debit': 0.0,
                    'credit': balance < 0.0 and -balance or balance,
                    'partner_id': rec.partner_id.id,
                    'account_id': rec.journal_id.default_account_id.id if balance > 0.0 else rec.company_id.account_journal_payment_debit_account_id
                }
                line_ids.append((0, 0, credit_vals))
                move_dict = {
                    'narration': rec.name,
                    'ref': rec.name,
                    'journal_id': rec.journal_id.id,
                    'date': rec.clearance_date,
                    'line_ids':line_ids
                }
                return_check_move_id = move_obj.create(move_dict)
                return_check_move_id.action_post()
                rec.return_check_move_id = return_check_move_id
                rec.cleared=True
                # reconcile with the invoice
                (rec.return_check_move_id.line_ids + rec.line_ids) \
                                        .filtered(lambda line: not line.reconciled and line.account_id.account_type == 'asset_current' and line
                                                  .partner_id ==rec.partner_id).reconcile()

class account_payment_register(models.TransientModel):
    _inherit = 'account.payment.register'

    payment_method_code = fields.Char(related='payment_method_line_id.code')
    check_type = fields.Selection([('direct', 'Direct'), ('outstand', 'Outstanding')], 'Check type')
    clearance_date = fields.Date('Check clearance date')

    def _create_payment_vals_from_wizard(self, batch_result):
        # print('##########################################################3')
        payment_vals = super(account_payment_register, self)._create_payment_vals_from_wizard(batch_result)
        payment_vals.update(
            {
                'check_type': self.check_type,
                'clearance_date': self.clearance_date,
            }
        )
        return payment_vals



