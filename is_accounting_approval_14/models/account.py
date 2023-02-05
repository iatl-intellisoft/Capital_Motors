##############################################################################
#    Description: Accounting Approval                                        #
#    Author: IATL-IntelliSoft Software                                       #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################


from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from . import amount_to_ar
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
    payment_method = fields.Many2one('account.payment.method')
    payment_method_name = fields.Char('Payment Method Name', related='payment_method.name')

# Add financial approval
class finance_approval(models.Model):
    _name = 'finance.approval'
    _description = 'A model for tracking finance approvals.'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Details', compute='_get_description', store=True, readonly=True)
    ca_app_id = fields.Many2one('res.users', string="Validated By")
    finance_approval_line_ids = fields.One2many('finance.approval.line', 'finance_id',
                                                string='Finance Approval Details')
    approval_no = fields.Char('Approval No.', help='Auto-generated Approval No. for finance approvals')
    requester = fields.Char('Requester', required=True, default=lambda self: self.env.user.name)
    request_amount = fields.Float('Requested Amount', required=True)
    request_currency = fields.Many2one('res.currency', 'Currency',
                                       default=lambda self: self.env.user.company_id.currency_id)
    request_amount_words = fields.Char(string='Amount in Words', readonly=True, default=False, copy=False,
                                       compute='_compute_text', translate=True)
    fa_date = fields.Date('Date', copy=False)
    department_id = fields.Many2one('hr.department', string="Department")
    beneficiary = fields.Char('Beneficiary')
    reason = fields.Char('Reason')
    expense_item = fields.Char('Expense Item')
    state = fields.Selection(
        [('draft', 'Draft'), ('department_approval', 'Department Approval'), ('to_approve', 'Financial Approval'),
         ('gm_approval', 'General Manager Approval'), ('ready', 'Ready for Payment'), ('reject', 'Rejected'),
         ('validate', 'Validated')],
        string='Finance Approval Status', default='draft')
    exp_account = fields.Many2one('account.account', string="Expense or Debit Account",store=True, copy=False)
    journal_id = fields.Many2one('account.journal', 'Bank/Cash Journal',
                                 help='Payment journal.', copy=False,
                                 domain=[('type', 'in', ['bank', 'cash'])])
    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True, copy=False)
    payment_id = fields.Many2one('account.payment', 'Account Payment', readonly=True, copy=False)
    mn_remarks = fields.Text('Manager Remarks', copy=False)
    auditor_remarks = fields.Text('Reviewer Remarks', copy=False)
    fm_remarks = fields.Text('Finance Man. Remarks', copy=False)
    gm_remarks = fields.Text('General Man. Remarks', copy=False)
    view_remarks = fields.Text('View Remarks', readonly=True, compute='_get_remarks', store=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    manager_id = fields.Many2one('res.users', string='Manager')
    partner_id = fields.Many2one('res.partner', string='Vendor',store=True, copy=False)
    mn_app_id = fields.Many2one('res.users', string="Manager Approval By")
    fm_app_id = fields.Many2one('res.users', string="Finance Approval By")
    gm_app_id = fields.Many2one('res.users', string="GM Approval By")
    at_app_id = fields.Many2one('res.users', string="Validated By")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    analytic_account = fields.Many2one('account.analytic.account', string='Cost/Profit Center', copy=False)
    check_no = fields.Char('Check No.', copy=False)
    #check_bank_name = fields.Many2one('bank.bank', 'Check Bank') # Move to Seprate module
    check_bank_branch = fields.Char('Check Bank Branch', copy=False)
    check_date = fields.Date('Check Date', copy=False)
    payment_method = fields.Many2one('account.payment.method', copy=False)
    payment_method_name = fields.Char('Payment Method Name', related='payment_method.name')
    gm_approvement = fields.Boolean('Require GM Approval?', default=True)
    admin_finance = fields.Boolean('Administration Request?', default=True)

    def move_without_check_currency(self):
        if not self.fa_date:
            raise ValidationError(_("Please Add Date!"))
        entrys = []
        rate = 0.0
        total = 0.0
        # if self.on_credit:
        #     credit_account = self.credit_account_id
        #     journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        # else:
        credit_account = self.journal_id.default_account_id
        journal = self.journal_id
        if self.finance_approval_line_ids:
            currency_rate_diff = (
                self.env["res.currency.rate"]
                .search(
                    [
                        ("currency_id", "=", self.request_currency.id),
                        ("name", "=", self.fa_date),
                    ],
                    limit=1,
                )
                .inverse_company_rate
            )
            if not currency_rate_diff:
                currency_rate_diff = (
                    self.env["res.currency.rate"]
                    .search(
                        [
                            ("currency_id", "=", self.request_currency.id),
                            ("name", "<", self.fa_date),
                        ],
                        limit=1,
                    )
                    .inverse_company_rate
                )
            if currency_rate_diff:
                rate = currency_rate_diff
            for line1 in self.finance_approval_line_ids:

                #     for rate3 in self.request_currency.rate_ids:
                #         rate = rate3.inverse_company_rate
                if not line1.exp_account:
                    raise ValidationError(_("Please select account!"))
                total = line1.amount
                credit_vals = {
                    'name': self.reason,
                    'partner_id': False,
                    'account_id': credit_account.id,
                    'currency_id': self.request_currency.id,
                    'amount_currency': -total,
                    'credit': total * rate,
                    'company_id': self.company_id.id,
                }
                entrys.append((0, 0, credit_vals))
                debit_val = {
                    'name': line1.name,
                    'partner_id': self.partner_id.id,
                    'account_id': line1.exp_account.id,
                    'currency_id': self.request_currency.id,
                    'amount_currency': total,
                    'debit': total * rate,
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

    def move_without_check(self):
        if not self.fa_date:
            raise ValidationError(_("Please Add Date!"))
        entrys = []
        total = 0.0
        # if self.on_credit:
        #     credit_account = self.credit_account_id
        #     journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        # else:
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
                    # 'analytic_account_id': line1.analytic_account_id.id,
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

    @api.model
    def create(self, vals):
        res = super(finance_approval, self).create(vals)
        # Get finance approval sequence no.
        next_seq = self.env['ir.sequence'].get('finance.approval.sequence')
        res.update({'approval_no': next_seq})
        return res

    # Overriding default get
    @api.model
    def default_get(self, fields):
        res = super(finance_approval, self).default_get(fields)
        # Get manager user id
        manager = self.env['res.users'].search([('id', '=', self.env.user.id)], limit=1).approval_manager.id
        if manager:
            res.update({'manager_id': manager})
        return res

    def department_approval(self):
        for rec in self:
            if rec.admin_finance == False:
                # Schedule activity for manager to approve
                vals = {
                    'activity_type_id': rec.env['mail.activity.type'].sudo().search(
                        [('name', 'like', 'Financial Approval')],
                        limit=1).id,
                    'res_id': rec.id,
                    'res_model_id': rec.env['ir.model'].sudo().search([('model', 'like', 'finance.approval')], limit=1).id,
                    'user_id': rec.manager_id.id and rec.manager_id.id or 1,
                    'summary': rec.name,
                }
                rec.env['mail.activity'].sudo().create(vals)
                # Change state
                rec.state = 'department_approval'

                # Update footer message
                if False:
                    message_obj = rec.env['mail.message']
                    message = _("State Changed  Confirm -> <em>%s</em>.") % (rec.state)
                    msg_id = rec.message_post(body=message)

            else:
                # Get advisor group
                fm_group_id = rec.env['res.groups'].sudo().search([('name', 'like', 'Advisor')], limit=1).id

                # First of all get all finance managers / advisors
                if fm_group_id:
                    rec.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (fm_group_id))

                    # Schedule activity for advisor(s) to approve
                    for fm in list(filter(lambda x: (
                            rec.env['res.users'].sudo().search([('id', '=', x)]).company_id == rec.company_id),
                                        rec.env.cr.fetchall())):
                        vals = {
                            'activity_type_id': rec.env['mail.activity.type'].sudo().search(
                                [('name', 'like', 'Financial Approval')],
                                limit=1).id,
                            'res_id': rec.id,
                            'res_model_id': rec.env['ir.model'].sudo().search([('model', 'like', 'finance.approval')],
                                                                            limit=1).id,
                            'user_id': fm[0] or 1,
                            'summary': rec.name,
                        }
                        rec.env['mail.activity'].sudo().create(vals)
                # Change state
                rec.state = 'to_approve'
    
                # Update footer message
                if False:
                    message_obj = rec.env['mail.message']
                    message = _("State Changed  Confirm -> <em>%s</em>.") % (rec.state)
                    msg_id = rec.message_post(body=message)

    # Approval
    def to_approve(self):
        for rec in self :
            # Schedule activity for finance manager to approve
            # Get finance manager group
            fm_group_id = rec.env['res.groups'].sudo().search([('name', 'like', 'Advisor')], limit=1).id
    
            # First of all get all finance managers / advisors
            if fm_group_id:
                rec.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (fm_group_id))
    
                # Schedule activity for advisor(s) to approve
                for fm in list(filter(lambda x: (
                        rec.env['res.users'].sudo().search([('id', '=', x)]).company_id == rec.company_id),
                                    rec.env.cr.fetchall())):
                    vals = {
                        'activity_type_id': rec.env['mail.activity.type'].sudo().search(
                            [('name', 'like', 'Financial Approval')],
                            limit=1).id,
                        'res_id': rec.id,
                        'res_model_id': rec.env['ir.model'].sudo().search([('model', 'like', 'finance.approval')],
                                                                        limit=1).id,
                        'user_id': fm[0] or 1,
                        'summary': rec.name,
                    }
                    rec.env['mail.activity'].sudo().create(vals)
            # Change state
            rec.state = 'to_approve'
            rec.mn_app_id = rec.env.user.id
    
            # Update footer message
            if False:
                message_obj = rec.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (rec.state)
                msg_id = rec.message_post(body=message)

        return True

    # Financial approval, i.e. actual approval step
    def financial_approval(self):
        for rec in self:
            if rec.gm_approvement == True:
                # Get general manager group
                gm_group_id = rec.env['res.groups'].sudo().search([('name', 'like', 'General Manager')], limit=1).id
    
                # First of all get all general manager(s)
                if gm_group_id:
                    rec.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (gm_group_id))
    
                    # Schedule activity for advisor(s) to approve
                    for gm in list(filter(lambda x: (
                            rec.env['res.users'].sudo().search([('id', '=', x)]).company_id == rec.company_id),
                                        rec.env.cr.fetchall())):
                        vals = {
                            'activity_type_id': rec.env['mail.activity.type'].sudo().search(
                                [('name', 'like', 'Financial Approval')],
                                limit=1).id,
                            'res_id': rec.id,
                            'res_model_id': rec.env['ir.model'].sudo().search([('model', 'like', 'finance.approval')],
                                                                            limit=1).id,
                            'user_id': gm[0] or 1,
                            'summary': rec.name,
                        }
                        rec.env['mail.activity'].sudo().create(vals)
    
                # Change state
                rec.state = 'gm_approval'
                rec.fm_app_id = rec.env.user.id
    
                # Update footer message
                if False:
                    message_obj = rec.env['mail.message']
                    message = _("State Changed  Confirm -> <em>%s</em>.") % (rec.state)
                    msg_id = rec.message_post(body=message)
            else:
                rec.state = 'ready'
            return True

        else:
            # Get validator group
            at_group_id = self.env['res.groups'].sudo().search([('name', 'like', 'Validator')], limit=1).id

            # First of all get all validator(s)
            if at_group_id:
                self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (at_group_id))

                # Schedule activity for validator(s) to validate
                for at in list(filter(lambda x: (
                        self.env['res.users'].sudo().search([('id', '=', x)]).company_id == self.company_id),
                                    self.env.cr.fetchall())):
                    vals = {
                        'activity_type_id': self.env['mail.activity.type'].sudo().search(
                            [('name', 'like', 'Financial Approval')],
                            limit=1).id,
                        'res_id': self.id,
                        'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'finance.approval')],
                                                                        limit=1).id,
                        'user_id': at[0] or 1,
                        'summary': self.name,
                    }
                    self.env['mail.activity'].sudo().create(vals)

            # Change state
            self.state = 'ready'
            self.fm_app_id = self.env.user.id

            # Update footer message
            if False:
                message_obj = self.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
                msg_id = self.message_post(body=message)

    # General manager approval
    def gm_approval(self):
        # Get validator group
        for rec in self:
            at_group_id = rec.env['res.groups'].sudo().search([('name', 'like', 'Validator')], limit=1).id
    
            # First of all get all general manager(s)
            if at_group_id:
                rec.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (at_group_id))
    
                # Schedule activity for general manager(s) to approve
                for at in list(filter(lambda x: (
                        rec.env['res.users'].sudo().search([('id', '=', x)]).company_id == rec.company_id),
                                    rec.env.cr.fetchall())):
                    vals = {
                        'activity_type_id': rec.env['mail.activity.type'].sudo().search(
                            [('name', 'like', 'Financial Approval')],
                            limit=1).id,
                        'res_id': rec.id,
                        'res_model_id': rec.env['ir.model'].sudo().search([('model', 'like', 'finance.approval')],
                                                                        limit=1).id,
                        'user_id': at[0] or 1,
                        'summary': rec.name,
                    }
                    rec.env['mail.activity'].sudo().create(vals)
    
            # Change state
            rec.state = 'ready'
            rec.gm_app_id = rec.env.user.id
    
            # Update footer message
            if False:
                message_obj = rec.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (rec.state)
                msg_id = rec.message_post(body=message)

    # Generate name of approval automatically
    @api.depends('approval_no', 'requester', 'beneficiary')
    def _get_description(self):
        self.name = ""
        for rec in self :
            rec.name = (rec.approval_no and ("Approval No: " + str(rec.approval_no)) or " ") + "/" + (
                    rec.requester and ("Requester: " + rec.requester) or " ") + "/" \
                        + (rec.beneficiary and ("Beneficiary: " + rec.beneficiary) or " ") + "/" + (
                                rec.reason and ("Reason: " + rec.reason) or " ")

    # Return request amount in words
    @api.depends('request_amount', 'request_currency')
    def _compute_text(self):
        for rec in self :
            rec.request_amount_words = amount_to_ar.amount_to_text_ar(rec.request_amount,
                                                                       rec.request_currency.narration_ar_un,
                                                                       rec.request_currency.narration_ar_cn)

    # Generate remarks
    @api.depends('mn_remarks', 'auditor_remarks', 'fm_remarks', 'gm_remarks')
    def _get_remarks(self):
        for rec in self:
            rec.view_remarks = (rec.mn_remarks and ("Manager Remarks: " + str(rec.mn_remarks)) or " ") + "\n\n" + (
                                rec.auditor_remarks and ("Account Manager Remarks: " + str(rec.auditor_remarks)) or " ") + "\n\n" + (
                                rec.fm_remarks and ("Financial Man. Remarks: " + rec.fm_remarks) or " ") + "\n\n" + (
                                rec.gm_remarks and ("General Man. Remarks: " + rec.gm_remarks) or " ")

    # Validation
    @api.constrains('request_amount')
    def request_amount_validation(self):
        if self.request_amount <= 0:
            raise ValidationError(_("Requested amount must be greater than zero!"))

    # validate that payments through checks allowed only for partners
    # @api.constrains('payment_method')
    # def request_amount_validation(self):
    #     if self.payment_method.name == 'Checks' and not self.partner_id:
    #         raise ValidationError(_("Checks are only allowed for vendors!"))

    # validate debit account when vendor selected
    # @api.constrains('exp_account', 'partner_id')
    # def check_account(self):
    #     if self.partner_id and self.exp_account.user_type_id.name != 'Payable':
    #         raise ValidationError(_("Debit account must be of type 'Payable' when selecting a vendor!"))

    def cancel_button(self):
        if self.move_id:
            self.move_id.button_cancel()
            self.move_id.unlink()
        if self.payment_id:
            self.payment_id.action_draft()
        self.state = 'draft'

    # Reject finance approval
    def reject(self):
        for rec in self:
            rec.state = 'reject'
            # Update footer message
            if False:
                message_obj = rec.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (rec.state)
                msg_id = rec.message_post(body=message)

    def validate(self):
        self.activity_ids.unlink()
        line_ids = []
        if not self.finance_approval_line_ids:
            raise ValidationError(_("Please Add Finance Approval Details!"))
        for x in self.finance_approval_line_ids:
            line = (0, 0, {
                'name': x.name,
                'account_id': x.exp_account.id,
                # 'analytic_account_id': x.analytic_account_id.id,
                'amount': x.amount,

            })
            line_ids.append(line)

        # if not self.exp_account:
        #     raise ValidationError(_("Expense or debit account must be selected!"))

        if not self.journal_id and not self.bank_journal_id and not self.on_credit:
            raise ValidationError(_("Journal must be selected!"))

        # account move entry
        if self.request_currency != self.env.user.company_id.currency_id:
            # corresponding details in account_move_line
            if self.payment_method.name == 'Manual':
                # if self.payment_method_code != 'check_printing':
                self.move_id = self.env['account.move'].create(self.move_without_check_currency())
                self.state = 'validate'
                self.move_id.action_post()
                self.ca_app_id = self.env.user.id
            elif self.payment_method.name == 'Checks':
                self.move_id = self.env['account.move'].create(self.move_without_check_currency())
                self.state = 'validate'
                self.ca_app_id = self.env.user.id

        if self.request_currency == self.env.user.company_id.currency_id:
            # corresponding details in account_move_line
            if self.payment_method.name == 'Manual':
                # if self.payment_method_code != 'check_printing':
                self.move_id = self.env['account.move'].create(self.move_without_check())
                self.state = 'validate'
                self.move_id.action_post()
                self.ca_app_id = self.env.user.id
            elif self.payment_method.name == 'Checks':
                self.move_id = self.env['account.move'].create(self.move_without_check())
                self.state = 'validate'
                self.ca_app_id = self.env.user.id

    def set_to_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.mn_app_id = None
            rec.fm_app_id = None
            rec.gm_app_id = None
            rec.at_app_id = None
            # Update footer message
            if False:
                message_obj = rec.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (rec.state)
                msg_id = rec.message_post(body=message)
