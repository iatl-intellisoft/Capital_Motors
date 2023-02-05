#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#    Description: Accounting Approval                                        #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################


from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import Warning, ValidationError, UserError


##############################################
class FinanceApprovalCheckLines(models.Model):
    _name = 'finance.approval.check.line'
    _description = 'Finance Approval Checks.'

    finance_id = fields.Many2one('finance.approval', string='Finance Approval', ondelete="cascade")
    Account_No = fields.Char(string='Account No')
    Check_no = fields.Char('Check No', required=True)
    Bank_id = fields.Many2one(related='journal_id.bank_id')
    check_date = fields.Date('Check Date', required=True)
    journal_id = fields.Many2one('account.journal', 'Bank/Cash Journal',
                                 help='Payment journal.',
                                 domain="[('type', 'in', ['bank'])]")
    exp_account = fields.Many2one('account.account', string="Expense or Debit Account", required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    amount = fields.Float('Check Amount', required=True)


########################################
class FinanceApprovalLine(models.Model):
    _name = 'finance.approval.line'
    _description = 'Finance Approval details.'

    finance_id = fields.Many2one('finance.approval', string='Finance Approval', ondelete="cascade")
    name = fields.Char('Narration', required=True)
    amount = fields.Float('Amount', required=True)
    notes = fields.Char('Notes')
    exp_account = fields.Many2one('account.account', string="Expense or Debit Account")
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    partner_id = fields.Many2one('res.partner', string='Partner')
    payment_method_name = fields.Many2one('account.payment.method')
    pa_name = fields.Char(related="payment_method_name.name")


#####################################
# add financial approval
class FinanceApproval(models.Model):
    _name = 'finance.approval'
    _description = 'A model for tracking finance approvals.'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'approval_no'

    approval_no = fields.Char('Approval No.', help='Auto-generated Approval No. for finance approvals')
    activity_ids = fields.One2many('mail.activity', 'finance_id', 'Activity')
    name = fields.Char('Details', compute='_get_description', store=True, readonly=True)
    fa_date = fields.Date('Date', default=fields.Date.today(), required=True)
    requester = fields.Char('Requester', required=True, default=lambda self: self.env.user.name)
    request_amount = fields.Float('Requested Amount', required=True)
    request_currency = fields.Many2one('res.currency', 'Currency',
                                       default=lambda self: self.env.user.company_id.currency_id)
    f_limit = fields.Float('Finance Manager Limit', default=lambda self: self.env.user.company_id.f_limit)
    request_amount_words = fields.Char(string='Amount in Words', readonly=True, default=False, copy=False,
                                       compute='_compute_text', translate=True)
    department_id = fields.Many2one('hr.department', string="Department")
    beneficiary = fields.Many2one('res.partner', 'Beneficiary')
    reason = fields.Char('Reason', required=True)
    expense_item = fields.Char('Expense Item')
    state = fields.Selection([('draft', 'Request'),
                              ('dir_app', 'Direct Manager Approval'),
                              ('fm_app', 'Financial Manager Approval'),
                              ('au_app', 'Auditor Approval'),
                              ('gm_app', 'General Manager Approval'),
                              ('ca_app', 'To validate'),
                              ('reject', 'Rejected'),
                              ('validate', 'Validated'),
                              ('cleared', 'Cleared')],
                             string='Finance Approval Status', default='draft')
    manager_id = fields.Many2one('res.users', string='Approve')
    fc_app_id = fields.Many2one('res.users', string='Approve FC')
    au_app_id = fields.Many2one('res.users', string="Manager Approval By")
    gm_app_id = fields.Many2one('res.users', string="Financial  Approval By")
    ca_app_id = fields.Many2one('res.users', string="Validated By")
    exp_account = fields.Many2one('account.account', string="Expense or Debit Account")
    payment_method = fields.Selection(
        selection=[('cash', 'Cash'), ('cheque', 'Cheque'), ('transfer', 'Transfer'),
                   ('trust', 'Trust'), ('other', 'Other')], string='Payment Method')
    payment_method_name = fields.Many2one('account.payment.method')
    payment_method_code = fields.Char(
        related='payment_method_name.code',
        help="Technical field used to adapt the interface to the payment type selected.")
    pa_name = fields.Char(related="payment_method_name.name")
    journal_id = fields.Many2one('account.journal', 'Bank/Cash Journal',
                                 help='Payment journal.',
                                 domain="[('type', 'in', ['bank', 'cash'])]")
    bank_journal_id = fields.Many2one('account.journal', 'Check bank Journal',
                                 help='Payment journal.',
                                 domain=[('type', '=', 'bank')])
    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True)
    mn_remarks = fields.Text('Manager Remarks')
    auditor_remarks = fields.Text('Reviewer Remarks')
    fm_remarks = fields.Text('Finance Man. Remarks')
    gm_remarks = fields.Text('General Man. Remarks')
    view_remarks = fields.Text('View Remarks', readonly=True, compute='_get_remarks', store=True)
    partner_id = fields.Many2one('res.partner', string='Supplier')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)

    # add company_id to allow this module to support multi-company
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    # adding analytic account
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic Account/Cost Center')

    checks_id = fields.One2many('check_followups.check_followups', 'finance_id', 'chq Ref')
    finance_approval_line_ids = fields.One2many('finance.approval.line', 'finance_id',
                                                string='Finance Approval Details')
    finance_approval_check_line_ids = fields.One2many('finance.approval.check.line', 'finance_id',
                                                string='Finance Approval Details')
    custody = fields.Boolean(string='Custody')
    department_manager_id = fields.Many2one('res.users', string="Department Manager", related='department_id.manager_id.user_id')
    department_approve = fields.Boolean('Approve', compute='_get_approve')
    on_credit = fields.Boolean('On Credit?')
    credit_account_id = fields.Many2one('account.account', 'Credit Account')
    is_custody = fields.Boolean('Is Custody?')
    is_done_custody = fields.Boolean('Done Custody')

    @api.depends('department_manager_id', 'state')
    def _get_approve(self):
        for rec in self:
            rec.department_approve = False
            if rec.state == 'dir_app' and rec.department_manager_id.id == self.env.user.id:
                rec.department_approve = True

    # Generate name of approval automatically
    @api.depends('approval_no', 'requester', 'beneficiary')
    def _get_description(self):
        self.name = (self.approval_no and ("Approval No: " + str(self.approval_no)) or " ") + "/" + (
            self.requester and ("Requester: " + self.requester) or " ") + "/" \
                    + (self.beneficiary and ("Beneficiary: " + self.beneficiary) or " ") + "/" + (
                        self.reason and ("Reason: " + self.reason) or " ")

    # Return request amount in words
    @api.depends('request_amount', 'request_currency')
    def _compute_text(self):
        from . import money_to_text_ar
        for r in self:
            r.request_amount_words = money_to_text_ar.amount_to_text_arabic(r.request_amount,
                                                                            r.request_currency.name)

    # Generate name of approval automatically
    @api.depends('mn_remarks', 'auditor_remarks', 'fm_remarks', 'gm_remarks')
    def _get_remarks(self):
        self.view_remarks = (self.mn_remarks and ("Manager Remarks: " + str(self.mn_remarks)) or " ") + "\n\n" + (
            self.auditor_remarks and ("Account Manager Remarks: " + str(self.auditor_remarks)) or " ") + "\n\n" + (
                                self.fm_remarks and ("Financial Man. Remarks: " + self.fm_remarks) or " ") + "\n\n" + (
                                self.gm_remarks and ("General Man. Remarks: " + self.gm_remarks) or " ")

    # validation
    @api.constrains('request_amount')
    def request_amount_validation(self):
        if self.request_amount <= 0:
            raise Warning(_("Request Amount Must be greater than zero!"))

    @api.model
    def create(self, vals):
        res = super(FinanceApproval, self).create(vals)
        # get finance approval sequence no.
        next_seq = self.env['ir.sequence'].get('finance.approval.sequence')
        res.update({'approval_no': next_seq})
        return res

    ############################################
    # added to allow for Direct manager approval
    def action_sent(self):
        state = 'dir_app'
        self.state = state
        return True

    # added to allow for Finance approval
    def manager_approval(self):
        self.activity_ids.unlink()
        users = self.env['res.groups'].sudo().search([('id', '=',
                                                self.env.ref('account.group_account_manager').id)],
                                              limit=1).users
        for user in users:
            vals = {
                'activity_type_id': self.env['mail.activity.type'].sudo().search(
                    [('name', 'like', 'Email')],
                    limit=1).id,
                'res_id': self.id,
                'finance_id': self.id,
                'res_model_id': self.env['ir.model'].sudo().search(
                    [('model', 'like', 'finance.approval')],
                    limit=1).id,
                'user_id': user.id,
                'summary': 'You have New Finance Approval' + ' ' + str(self.approval_no),
            }
            self.activity_ids = self.env['mail.activity'].sudo().create(vals)
        state = 'fm_app'
        self.manager_id = self.env.user.id
        self.state = state
        return True

    # added to allow for Finance approval
    def finance_approval(self):
        state = 'au_app'
        self.fc_app_id = self.env.user.id
        self.state = state
        return True

    # added to allow for Finance approval
    def auditor_approval(self):
        if self.pa_name == 'Check Followup' and not self.gm_app_id:
            state = 'gm_app'
        else:
            state = 'ca_app'
        self.au_app_id = self.env.user.id
        self.state = state
        return True

    def general_approval(self):
        state = 'ca_app'
        self.gm_app_id = self.env.user.id
        self.state = state
        return True

    #############################################
    def cancel_button(self):
        self.move_id.button_cancel()
        self.move_id.unlink()
        self.state = 'draft'

    # reject finance approval
    def reject(self):

        self.state = 'reject'
        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

    def action_view_checks(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('ii_check_management_15.check_followups_vendor').read()[0]

        checks = self.mapped('checks_id')
        if len(checks) > 1:
            action['domain'] = [('id', 'in', checks.ids)]
        elif checks:
            action['views'] = [(self.env.ref('ii_check_management_15.check_followups_form').id, 'form')]
            action['res_id'] = checks.id
        return action

    # validate, i.e. post to account moves
    def move_check_followups(self):
        if self.finance_approval_check_line_ids:
            for line1 in self.finance_approval_check_line_ids:
                if not line1.exp_account:
                    raise ValidationError(_("Please select account!"))
                debit_vals = {
                    'name': self.approval_no + str(line1.Check_no),
                    'partner_id': self.partner_id.id,
                    'account_id': line1.exp_account.id,
                    'currency_id': self.request_currency.id,
                    'amount_currency': line1.amount,
                    'debit': line1.amount / self.request_currency.rate,
                    #'analytic_account_id': line1.analytic_account_id.id,
                    'company_id': self.company_id.id,
                }
                check_state = 'out_standing'
                credit_vals = {
                    'name': self.approval_no + str(line1.Check_no),
                    'partner_id': self.partner_id.id,
                    'account_id': line1.journal_id.company_id.account_journal_payment_credit_account_id.id,
                    'currency_id': self.request_currency.id,
                    'amount_currency': -line1.amount,
                    'credit': line1.amount / self.request_currency.rate,
                    'company_id': self.company_id.id,
                }
                vals = {
                    'journal_id': line1.journal_id.id,
                    'move_type': 'entry',
                    'date': datetime.today(),
                    'ref': self.approval_no,
                    'company_id': self.company_id.id,
                    'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
                }
                move = self.env['account.move'].create(vals)
                move.action_post()

                dictionary = {
                    'name': self.approval_no,
                    # 'account_holder': self.company_id.id,
                    'Date': line1.check_date,
                    'finance_id': self.id,
                    'finance_line_id': line1.id,
                    'bank_id': line1.Bank_id.id,
                    # 'beneficiary_id': self.partner_id.id,
                    'amount': line1.amount,
                    'currency_id': self.request_currency.id,
                    'check_no': line1.Check_no,
                    'approval_check': True,
                    'state': check_state,
                    'type': 'outbound',
                    'communication': self.approval_no,
                    'company_id': self.company_id.id,
                }
                check = self.env['check_followups.check_followups'].create(dictionary)
                log = {
                    'move_id': move.id,
                    'name': self.approval_no,
                    'date': line1.check_date,
                    'Check': check.id,
                    'finance_id': self.id,
                }
                # log_obj = self.env['check_followups.checklogs']
                self.env['check_followups.checklogs'].create(log)

        return vals

    def move_without_check(self):
        entrys = []
        total = 0.0
        if self.on_credit:
            credit_account = self.credit_account_id
            journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        else:
            credit_account = self.journal_id.default_account_id
            journal = self.journal_id
        if self.finance_approval_line_ids:
            for line1 in self.finance_approval_line_ids:
                if not line1.exp_account:
                    raise ValidationError(_("Please select account!"))
                total = line1.amount
                credit_vals = {
                    'name': self.reason,
                    'partner_id': False,
                    'account_id': credit_account.id,
                    'credit': total,
                    'company_id': self.company_id.id,
                }
                entrys.append((0, 0, credit_vals))
                debit_val = {
                    'name': line1.name,
                    'partner_id': self.partner_id.id,
                    'account_id': line1.exp_account.id,
                    'debit': total,
                    #'analytic_account_id': line1.analytic_account_id.id,
                    'company_id': self.company_id.id,
                }
                # print "debit val", debit_val
                entrys.append((0, 0, debit_val))
        vals = {
            'journal_id': journal.id,
            'date': self.fa_date,
            'ref': self.approval_no,
            'company_id': self.company_id.id,
            'line_ids': entrys
        }
        return vals

    def validate(self):
        self.activity_ids.unlink()
        line_ids = []
        for x in self.finance_approval_line_ids:
            line = (0, 0, {
                'name': x.name,
                'account_id': x.exp_account.id,
                #'analytic_account_id': x.analytic_account_id.id,
                'amount': x.amount,

            })
            line_ids.append(line)

        if not self.exp_account and self.custody == True:
            raise ValidationError(_("Expense or debit account must be selected!"))

        if not self.journal_id and not self.bank_journal_id and not self.on_credit:
            raise ValidationError(_("Journal must be selected!"))

        # account move entry
        if self.request_currency == self.env.user.company_id.currency_id:
            # corresponding details in account_move_line
            if self.payment_method_code != 'check_printing':
                self.move_id = self.env['account.move'].create(self.move_without_check())
                self.move_id.action_post()
                self.state = 'validate'
                self.ca_app_id = self.env.user.id
            elif self.payment_method_code == 'check_printing':
                self.move_check_followups()
                self.state = 'validate'
                self.ca_app_id = self.env.user.id
        elif self.request_currency != self.env.user.company_id.currency_id:
            if self.payment_method_code != 'check_printing':
                entrys = []
                if self.finance_approval_line_ids:
                    total = 0
                    for line1 in self.finance_approval_line_ids:
                        total += line1.amount
                    if self.on_credit:
                        credit_account = self.credit_account_id
                        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
                    else:
                        credit_account = self.journal_id.default_account_id
                        journal = self.journal_id
                    credit_vals = {
                        'name': self.reason,
                        'partner_id': self.partner_id.id,
                        'account_id': credit_account.id,
                        'currency_id': self.request_currency.id,
                        'amount_currency': -total,
                        'credit': total / self.request_currency.rate,
                        'company_id': self.company_id.id,
                    }
                    entrys.append((0, 0, credit_vals))
                    # if total != self.request_amount:
                    #     raise UserError('Request amount and sum of details amount must be equal ')
                    for line in self.finance_approval_line_ids:
                        if not line.exp_account:
                            raise ValidationError(_("Please select account!"))
                        # if line.pa_name == 'Manual':
                        debit_val = {
                            'name': line.name,
                            'partner_id': line.partner_id.id,
                            'account_id': line.exp_account.id,
                            'debit': line.amount / self.request_currency.rate,
                            'currency_id': self.request_currency.id,
                            'amount_currency': line.amount,
                            #'analytic_account_id': line.analytic_account_id.id,
                            'company_id': self.company_id.id,
                        }
                        # print "debit val", debit_val
                        entrys.append((0, 0, debit_val))
                else:
                    debit_vals = {
                        'name': self.name,
                        'partner_id': self.partner_id.id,
                        'account_id': self.exp_account.id,
                        'debit': self.request_amount > 0.0 and self.request_amount or 0.0,
                        #'analytic_account_id': self.analytic_account.id,
                        'credit': self.request_amount < 0.0 and -self.request_amount or 0.0,
                        'company_id': self.company_id.id,
                    }
                    entrys.append((0, 0, debit_vals))
                vals = {
                    'journal_id': journal.id,
                    'date': self.fa_date,
                    'ref': self.approval_no,
                    'company_id': self.company_id.id,
                    'line_ids': entrys
                    # 'line_ids': [(0, 0, debit_val), (0, 0, credit_val)]
                }
                # add lines
                self.move_id = self.env['account.move'].create(vals)
                self.move_id.action_post()
                # Change state if all went well!
                self.state = 'validate'
                self.ca_app_id = self.env.user.id
            elif self.payment_method_code == 'check_printing':
                self.move_check_followups()
                self.state = 'validate'
                self.ca_app_id = self.env.user.id
        else:
            raise Warning(_("An issue was faced when validating!"))

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)
        self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()

    def set_to_draft(self):
        self.state = 'draft'
        self.manager_id = None
        self.fc_app_id = None
        self.au_app_id = None
        self.gm_app_id = None
        self.ca_app_id = None

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    finance_id = fields.Many2one('finance.approval', string='Activity')
