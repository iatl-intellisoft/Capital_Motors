##############################################################################
#    Description: HR Overtime Customization                                        #
#    Author: IntelliSoft Software                                            #
#    Date: Dec 2017 -  Till Now                                              #
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrMonthlyloan(models.Model):
    _name = 'hr.monthlyloan'
    _description = 'Hr Monthly Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char('Loan')
    date = fields.Date(string="Loan Date", default=fields.Date.today())
    date_pay = fields.Date(string="Loan Pay Date", readonly=True)
    employee_id = fields.Many2one(
        'hr.employee', string="Employee", default=_default_employee, required=True)
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department")
    loan_amount = fields.Float(string="Loan Amount", required=True)
    employee_salary = fields.Float(
        string="Employee Salary", compute='_compute_salary')
    employee_account = fields.Many2one(
        'account.account', string="Debit Account")
    loan_account = fields.Many2one('account.account', string="Credit Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    move_id = fields.Many2one(
        'account.move', string="Journal Entry", readonly=True)
    move_id_pay = fields.Many2one(
        'account.move', string="Loan Payment Entry", readonly=True)
    payment_account = fields.Many2one(
        'account.account', string="Payment Account")
    state = fields.Selection(
        [('draft', 'To Submit'), ('confirm', 'To Approve'),
         ('approve', 'Approved by HR'), ('done', 'Done'), ('paid', 'Paid'),
         ('refuse', 'Refused')],
        'Status', default='draft', readonly=True)

    # @api.model
    # def _needaction_domain_get(self):
    #     hr = self.employee_id.user_id.has_group('hr.group_hr_manager')
    #     gm = self.employee_id.user_id.has_group('is_hr_matwa.group_hr_general_manager')
    #     account = self.employee_id.user_id.has_group('account.group_account_manager')
    #
    #     hr_approve = hr and 'confirm' or None
    #     account_approve = account and 'approve' or None
    #
    #     return [('state', 'in', (hr_approve, account_approve))]

    def loan_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def loan_approve(self):
        for rec in self:
            rec.state = 'approve'

    def action_paid(self):
        can_close = False
        loan_obj = self.env['hr.monthlyloan']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        created_move_ids = []
        loan_ids = []
        for loan in self:
            if loan.state == 'done':
                loan_pay_date = fields.Date.today()
                amount = loan.loan_amount
                loan_name = 'Short Loan Payment For ' + loan.employee_id.name
                reference = loan.name
                journal_id = loan.journal_id.id
                move_obj = self.env['account.move']
                move_line_obj = self.env['account.move.line']
                currency_obj = self.env['res.currency']
                created_move_ids = []
                loan_ids = []
                if loan.payment_account.id:
                    debit_account = loan.payment_account.id
                if not loan.payment_account.id:
                    debit_account = loan.loan_account.id
                line_ids = []
                debit_sum = 0.0
                credit_sum = 0.0
                move_dict = {
                    'narration': loan_name,
                    'ref': reference,
                    'journal_id': journal_id,
                    'date': loan_pay_date,
                }

                debit_line = (0, 0, {
                    'name': loan_name,
                    'partner_id': self.employee_id.related_partner_id.id,
                    'account_id': debit_account,
                    'journal_id': journal_id,
                    'date': loan_pay_date,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'analytic_distribution': False,
                    'tax_line_id': 0.0,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
                credit_line = (0, 0, {
                    'name': loan_name,
                    'partner_id': self.employee_id.related_partner_id.id,
                    'account_id': loan.employee_account.id,
                    'journal_id': journal_id,
                    'date': loan_pay_date,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'analytic_distribution': False,
                    'tax_line_id': 0.0,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - \
                    credit_line[2]['debit']
                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                loan.write({'move_id_pay': move.id, 'date_pay': loan_pay_date})
                move.action_post()
        self.state = 'paid'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.loan.short') or ' '
        res = super(HrMonthlyloan, self).create(vals_list)
        return res

    @api.depends('employee_id')
    def _compute_salary(self):
        for rec in self:
            rec.employee_salary = 0
        if rec.employee_id:
            rec.employee_salary = rec.employee_id.contract_id.wage

    def loan_validate(self):
        if not self.employee_account or not self.loan_account or not self.journal_id:
            raise UserError(
                _("You must enter employee account & Loan account and journal to approve "))
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        loan_ids = []
        for monthh_loan in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            loan_date = monthh_loan.date
            company_currency = monthh_loan.employee_id.company_id.currency_id.id
            current_currency = self.env.user.company_id.currency_id.id
            amount = monthh_loan.loan_amount
            employee_salary = self.employee_id.contract_id.wage
            if amount > employee_salary/2:
                raise UserError(
                    _("Loan should not exceed half of employee salary"))
            loan_name = 'Short Loan For ' + monthh_loan.employee_id.name
            reference = monthh_loan.name
            journal_id = monthh_loan.journal_id.id
            move_dict = {
                'narration': loan_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': loan_date,
            }
            debit_line = (0, 0, {
                'name': loan_name,
                'partner_id': self.employee_id.related_partner_id.id,
                'account_id': monthh_loan.employee_account.id,
                'journal_id': journal_id,
                'date': loan_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_distribution': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': loan_name,
                'partner_id': self.employee_id.related_partner_id.id,
                'account_id': monthh_loan.loan_account.id,
                'journal_id': journal_id,
                'date': loan_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_distribution': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            monthh_loan.write({'move_id': move.id, 'date': loan_date})
            move.action_post()
            self.state = 'done'

    @api.constrains('loan_amount')
    def _loan_amount(self):
        if self.loan_amount:
            salary = self.employee_salary
            allowable_loan = salary * 35 / 100
            if self.loan_amount > allowable_loan:
                raise UserError(
                    _("Monthly Loan Cannot Exceed 35% of The Employee's Salary!"))

    def loan_refuse(self):
        for rec in self:
            rec.state = 'refuse'

    def loan_reset(self):
        for rec in self:
            rec.state = 'draft'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    _("Warning! You cannot delete a Loan which is in %s state.") % (rec.state))
            return super(HrMonthlyloan, self).unlink()
