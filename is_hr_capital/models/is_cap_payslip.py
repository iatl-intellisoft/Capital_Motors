from odoo import models, fields, api, _
from datetime import datetime, time
import calendar
from odoo.tools.float_utils import float_compare, float_is_zero

from odoo.exceptions import UserError, ValidationError
import base64
from odoo.tools.safe_eval import safe_eval


class CapPayslip(models.Model):
    _inherit = "hr.payslip"

    # bank_acct_num = fields.Char(string='Bank Account Number', related='employee_id.bank_account_id', store=True)
    code = fields.Char(string='Code', related='employee_id.code', store=True)

    absent_deduction = fields.Float(
        string='Absent Deduction', readonly=True, compute='compute_penalty')
    delay_deduction_hour = fields.Float(
        string='Delay Deduction Hour', readonly=True, compute='compute_penalty')
    delay_days_minutes = fields.Float(
        string='Delay Deduction Minutes', readonly=True, compute='compute_penalty')
    long_loan = fields.Float(
        string='Long Loan', readonly=True, compute='get_loan', store=True)
    short_loan = fields.Float(
        string='Advance Salary', readonly=True, compute='get_short_loan', store=True)
    grants = fields.Float(string='Grants % ')
    worked_days = fields.Float(
        string='Worked Days', compute='_compute_days', store=True)
    no_of_days = fields.Integer(
        string='No of Days', compute='_compute_days', store=True)
    net_salary = fields.Float(
        "Net Salary", compute='get_net_salary', store=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Batches', readonly=True,
                                     copy=False, states={'draft': [('readonly', False)]}, ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                    \n* If the payslip is confirmed by hr, the status is \'Confirmed\'.
                    \n* If the payslip is under verification, the status is \'Waiting\'.
                    \n* If the payslip is confirmed by account then status is set to \'Done\'.
                    \n* When user cancel payslip the status is \'Rejected\'.""")

    @api.depends('employee_id', 'contract_id')
    def compute_penalty(self):
        for rec in self:
            if rec.employee_id and rec.contract_id:
                employee_salary = rec.employee_id.contract_id.wage
                absent_days = 0
                delay_days_hour = 0
                delay_days_minutes = 0
                rec.delay_deduction_hour = 0.0
                rec.delay_days_minutes = 0.0
                rec.absent_deduction = 0.0
                penalty_ids = self.env['hr.emp.penalty'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date', '<=', rec.date_to), ('state', '=', 'done')])
                for pan in penalty_ids:
                    if pan.violation_id.deduction_type == 'day':
                        absent_days += pan.penalty*pan.penalty_amount
                    if pan.violation_id.deduction_type == 'hour':
                        delay_days_hour += pan.penalty*pan.penalty_amount
                    if pan.violation_id.deduction_type == 'minutes':
                        delay_days_minutes += pan.penalty*pan.penalty_amount
                rec.absent_deduction = (employee_salary / 30) * absent_days
                rec.delay_deduction_hour = (
                    employee_salary / 240) * delay_days_hour
                rec.delay_days_minutes = (
                    employee_salary / 14400) * delay_days_minutes

    # @api.depends('employee_id', 'date_from', 'date_to')
    # def compute_installment_ded(self):
    #     for rec in self:
    #         if rec.employee_id:
    #             installemnt_ids = self.env['hr.installment.line'].search(
    #                 [('employee_id', '=', rec.employee_id.id), ('date_to', '>=', rec.date_to)])
    #             for installemnt_id in installemnt_ids:
    #                 # finance = x.env['finance.approval'].search([('grand_id', '=', grand.id)])
    #                 if installemnt_id.state != 'paid':
    #                     payslip_date_to = rec.date_to
    #                     installment_date_to = installemnt_id.date_to
    #                     payslip_date_to = datetime.strptime(str(payslip_date_to), '%Y-%m-%d')
    #                     installment_date_to = datetime.strptime(str(installment_date_to), '%Y-%m-%d')
    #                     grand_month = installment_date_to.month
    #                     payslip_month = payslip_date_to.month
    #                     if grand_month == payslip_month:
    #                         installemnt_id.write({'mod_check': True})
    #                         rec.installment_ded += installemnt_id.deduction_mod
    #                     else:
    #                         rec.installment_ded += installemnt_id.deduction

    @api.depends('employee_id', 'line_ids')
    def get_net_salary(self):
        for rec in self:
            net = 0.00
            total = 0.00
            if rec.line_ids and rec.employee_id:
                payslip_line_ids = self.env['hr.payslip.line'].search([('employee_id', '=', rec.employee_id.id),
                                                                       ('code',
                                                                        '=', 'NET'),
                                                                       ('slip_id', '=', rec.id)])
                for slip in payslip_line_ids:
                    total = slip.total
            rec.net_salary = total

    @api.depends('date_from', 'date_to')
    def _compute_days(self):
        # str_now = datetime.now().date()
        days = 0
        month_range = 1
        for slip in self:
            if slip.date_from and slip.date_to:
                date_from = datetime.strptime(str(slip.date_from), '%Y-%m-%d')
                month_range = calendar.monthrange(
                    date_from.year, date_from.month)[1]
                date_to = datetime.strptime(str(slip.date_to), '%Y-%m-%d')
                days = (date_to - date_from).days + 1
            slip.no_of_days = days
            if month_range > 0:
                worked_days = float(days)/(month_range)
            else:
                raise UserError(_("Please Enter Valid Dates for this payslip "))
            if worked_days > 1.00:
                slip.worked_days = 1
            else:
                slip.worked_days = worked_days

    def action_hr_confirm(self):
        for rec in self:
            rec.compute_sheet()
            rec.state = 'confirm'

    @api.depends('employee_id', 'date_to', 'date_from')
    def compute_unpaid(self):
        for x in self:
            # if x.worked_days_line_ids:
            unpaid_sum = 0.0
            total_unpaid_salary = 0.0
            unpaid_ids = self.env['hr.leave'].search([('employee_id', '=', x.employee_id.id),
                                                      ('date_from', '>=',
                                                       x.date_from),
                                                      ('date_to', '<=', x.date_to),
                                                      ('holiday_status_id', '=', self.env.ref(
                                                          'hr_holidays.holiday_status_unpaid').id),
                                                      ('state', '=', 'validate')])
            if unpaid_ids:
                for leave in unpaid_ids:
                    # if worked_ids.code == 'Unpaid':
                    unpaid_sum += leave.number_of_days_temp
                employee_salary = x.employee_id.contract_id.wage
                total_unpaid_salary = employee_salary * unpaid_sum / 30
            x.unpaid_leave = total_unpaid_salary

    @api.depends('employee_id', 'date_to', 'date_from')
    def get_loan(self):
        for rec in self:
            if rec.employee_id:
                loan_ids = rec.env['hr.loan.line'].search(
                    [('employee_id', '=', rec.employee_id.id), ('paid', '=', False),
                     ('paid_date', '<=', rec.date_to), ('paid_date', '>=', rec.date_from), ('loan_id.state', '=', 'done')])
                for loan_id in loan_ids:
                    rec.long_loan = loan_id.paid_amount

    @api.depends('employee_id', 'date_to', 'date_from')
    def get_short_loan(self):
        for x in self:
            if x.employee_id:
                amount = 0.00
                loan_ids = x.env['hr.monthlyloan'].search(
                    [('employee_id', '=', x.employee_id.id), ('state', '=', 'done'), ('date', '>=', x.date_from),
                     ('date', '<=', x.date_to)])
                for loan in loan_ids:
                    amount += loan.loan_amount
                x.short_loan = amount

    def action_payslip_done(self):
        for payslip in self:
            if payslip.employee_id:
                payslip_obj = payslip.search(
                    [('employee_id', '=', payslip.employee_id.id), ('name', '=', payslip.name), ('state', '!=', 'done')])
                if len(payslip_obj) > 1:
                    raise UserError(
                        _("This Employee Already Took This Month's Salary!"))
            loan_ids = payslip.env['hr.loan.line'].search(
                [('employee_id', '=', payslip.employee_id.id), ('paid', '=', False)])
            for line in loan_ids:
                if line.paid_date >= payslip.date_from and line.paid_date <= payslip.date_to and line.loan_id.state == 'done':
                    if not line.paid:
                        # line.payroll_id = payslip.id
                        line.action_paid_amount()
                else:
                    line.payroll_id = False

            short_loan_ids = payslip.env['hr.monthlyloan'].search(
                [('employee_id', '=', payslip.employee_id.id), ('state', '=', 'done'),
                 ('date', '>=', payslip.date_from),
                 ('date', '<=', payslip.date_to)])
            for short_loan in short_loan_ids:
                short_loan.action_paid()
            """
                        Generate the accounting entries related to the selected payslips
                        A move is created for each journal and for each month.
                    """
            # res = super(HrPaySlip, self).action_payslip_done()
            precision = self.env['decimal.precision'].precision_get('Payroll')

            # Add payslip without run
            payslips_to_post = self.filtered(
                lambda slip: not slip.payslip_run_id)

            # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
            payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
            for run in payslip_runs:
                if run._are_payslips_ready():
                    payslips_to_post |= run.slip_ids

            # A payslip need to have a done state and not an accounting move.
            # payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)
            # print("here four",payslips_to_post)

            #
            for payslips_to_post in self:

                # Check that a journal exists on all the structures
                if any(not payslip.struct_id for payslip in payslips_to_post):
                    raise ValidationError(
                        _('One of the contract for these payslips has no structure type.'))
                if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
                    raise ValidationError(
                        _('One of the payroll structures has no account journal defined on it.'))

                # Map all payslips by structure journal and pay slips month.
                # {'journal_id': {'month': [slip_ids]}}
                slip_mapped_data = {
                    slip.struct_id.journal_id.id: {fields.Date().end_of(slip.date_to, 'month'): self.env['hr.payslip']} for slip
                    in payslips_to_post}
                for slip in payslips_to_post:
                    slip_mapped_data[slip.struct_id.journal_id.id][fields.Date().end_of(
                        slip.date_to, 'month')] |= slip

                for journal_id in slip_mapped_data:  # For each journal_id.
                    # For each month.
                    for slip_date in slip_mapped_data[journal_id]:
                        line_ids = []
                        debit_sum = 0.0
                        credit_sum = 0.0
                        date = slip_date
                        move_dict = {
                            'narration': '',
                            'ref': date.strftime('%B %Y'),
                            'journal_id': journal_id,
                            'date': date,
                        }

                        for slip in slip_mapped_data[journal_id][slip_date]:

                            move_dict['narration'] += slip.number or '' + \
                                ' - ' + slip.employee_id.name or ''
                            move_dict['narration'] += '\n'
                            for line in slip.line_ids.filtered(lambda line: line.category_id):
                                amount = -line.total if slip.credit_note else line.total
                                # Check if the line is the 'Net Salary'.
                                if line.code == 'NET':
                                    for tmp_line in slip.line_ids.filtered(lambda line: line.category_id):
                                        # Check if the rule must be computed in the 'Net Salary' or not.
                                        if tmp_line.salary_rule_id.not_computed_in_net:
                                            if amount > 0:
                                                amount -= abs(tmp_line.total)
                                            elif amount < 0:
                                                amount += abs(tmp_line.total)
                                if float_is_zero(amount, precision_digits=precision):
                                    continue
                                debit_account_id = line.salary_rule_id.account_debit.id
                                credit_account_id = line.salary_rule_id.account_credit.id

                                if debit_account_id:  # If the rule has a debit account.
                                    debit = amount if amount > 0.0 else 0.0
                                    credit = -amount if amount < 0.0 else 0.0

                                    existing_debit_lines = (
                                        line_id for line_id in line_ids if
                                        line_id['name'] == line.name
                                        and line_id['account_id'] == debit_account_id
                                        and line_id['analytic_account_id'] == (
                                            line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id)
                                        and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0)))
                                    debit_line = next(
                                        existing_debit_lines, False)

                                    if not debit_line:
                                        debit_line = {
                                            'name': line.name,
                                            'partner_id': payslip.employee_id.related_partner_id.id,
                                            'account_id': debit_account_id,
                                            'journal_id': slip.struct_id.journal_id.id,
                                            'date': date,
                                            'debit': debit,
                                            'credit': credit,
                                            'analytic_distribution': {line.salary_rule_id.analytic_account_id.id: 100} or {slip.contract_id.analytic_account_id.id: 100},
                                        }
                                        line_ids.append(debit_line)
                                    else:
                                        debit_line['debit'] += debit
                                        debit_line['credit'] += credit

                                if credit_account_id:  # If the rule has a credit account.
                                    debit = -amount if amount < 0.0 else 0.0
                                    credit = amount if amount > 0.0 else 0.0
                                    existing_credit_line = (
                                        line_id for line_id in line_ids if
                                        line_id['name'] == line.name
                                        and line_id['account_id'] == credit_account_id
                                        and line_id['analytic_account_id'] == (
                                            line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id)
                                        and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0))
                                    )
                                    credit_line = next(
                                        existing_credit_line, False)

                                    if not credit_line:
                                        credit_line = {
                                            'name': line.name,
                                            'partner_id': payslip.employee_id.related_partner_id.id,
                                            'account_id': credit_account_id,
                                            'journal_id': slip.struct_id.journal_id.id,
                                            'date': date,
                                            'debit': debit,
                                            'credit': credit,
                                            'analytic_distribution': {line.salary_rule_id.analytic_account_id.id: 100} or {slip.contract_id.analytic_account_id.id: 100},
                                        }
                                        line_ids.append(credit_line)
                                    else:
                                        credit_line['debit'] += debit
                                        credit_line['credit'] += credit

                        for line_id in line_ids:  # Get the debit and credit sum.
                            debit_sum += line_id['debit']
                            credit_sum += line_id['credit']

                        # The code below is called if there is an error in the balance between credit and debit sum.
                        if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                            acc_id = slip.journal_id.default_account_id.id
                            if not acc_id:
                                raise UserError(
                                    _('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                        slip.journal_id.name))
                            existing_adjustment_line = (
                                line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                            )
                            adjust_credit = next(
                                existing_adjustment_line, False)

                            if not adjust_credit:
                                adjust_credit = {
                                    'name': _('Adjustment Entry'),
                                    'partner_id': False,
                                    'account_id': acc_id,
                                    'journal_id': slip.journal_id.id,
                                    'date': date,
                                    'debit': 0.0,
                                    'credit': debit_sum - credit_sum,
                                }
                                line_ids.append(adjust_credit)
                            else:
                                adjust_credit['credit'] = debit_sum - \
                                    credit_sum

                        elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                            acc_id = slip.journal_id.default_account_id.id
                            if not acc_id:
                                raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                                    slip.journal_id.name))
                            existing_adjustment_line = (
                                line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                            )
                            adjust_debit = next(
                                existing_adjustment_line, False)

                            if not adjust_debit:
                                adjust_debit = {
                                    'name': _('Adjustment Entry'),
                                    'partner_id': False,
                                    'account_id': acc_id,
                                    'journal_id': slip.journal_id.id,
                                    'date': date,
                                    'debit': credit_sum - debit_sum,
                                    'credit': 0.0,
                                }
                                line_ids.append(adjust_debit)
                            else:
                                adjust_debit['debit'] = credit_sum - debit_sum

                        # Add accounting lines in the move
                        move_dict['line_ids'] = [
                            (0, 0, line_vals) for line_vals in line_ids]
                        move = self.env['account.move'].create(move_dict)
                        for slip in slip_mapped_data[journal_id][slip_date]:
                            slip.write({'move_id': move.id, 'date': date})

        # return super(CapPayslip, self).action_payslip_done()
        if any(slip.state == 'cancel' for slip in self):
            raise ValidationError(_("You can't validate a cancelled payslip."))
        self.write({'state': 'done'})
        self.mapped('payslip_run_id').action_close()
        if self.env.context.get('payslip_generate_pdf'):
            for payslip in self:
                if not payslip.struct_id or not payslip.struct_id.report_id:
                    report = self.env.ref(
                        'hr_payroll.action_report_payslip', False)
                else:
                    report = payslip.struct_id.report_id
                pdf_content, content_type = report.render_qweb_pdf(payslip.id)
                if payslip.struct_id.report_id.print_report_name:
                    pdf_name = safe_eval(payslip.struct_id.report_id.print_report_name, {
                                         'object': payslip})
                else:
                    pdf_name = _("Payslip")
                self.env['ir.attachment'].create({
                    'name': pdf_name,
                    'type': 'binary',
                    'datas': base64.encodestring(pdf_content),
                    'res_model': payslip._name,
                    'res_id': payslip.id
                })

    @api.constrains('name')
    def _no_duplicate_payslips(self):
        for rec in self:
            if self.employee_id:
                payslip_obj = self.search(
                    [('employee_id', '=', rec.employee_id.id), ('name', '=', rec.name)])
                if len(payslip_obj) > 1:
                    raise UserError(
                        _("This Employee Already Took his Month's Salary!"))


class CapPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verify'),
        ('close', 'Done'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')

    grants = fields.Float(string='Grants % ')

    def close_payslip_run(self):
        for slip in self:
            for slip_run in slip.slip_ids:
                slip_run.action_payslip_done()
        return super(CapPayslipRun, self).close_payslip_run()

    def action_hr_confirm(self):
        for slip in self:
            slip.state = 'confirm'
            for slip_run in slip.slip_ids:
                slip_run.action_hr_confirm()

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    _("Warning! You cannot delete a payslip which is in %s state.") % (rec.state))
        return super(CapPayslipRun, self).unlink()


class WizardPayslipRecompute(models.TransientModel):
    _name = 'wizard.payslip.recompute'
    _description = 'Wizard Payslip Recompute'

    def action_recompute_payslip(self):
        for rec in self:
            payslip_ids = self.env['hr.payslip'].browse(
                self.env.context.get('active_ids'))
            for emp in payslip_ids:
                emp.compute_sheet()
