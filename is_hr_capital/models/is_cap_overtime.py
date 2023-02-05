from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import babel


class HrOvertime(models.Model):
    _name = 'hr.overtime'
    _description = 'Hr Overtime'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def _is_department_manager(self):
        for rec in self:
            if rec.name.parent_id.user_id.id == rec.env.user.id or rec.name.manager_id.user_id.id == rec.env.user.id:
                rec.is_department_manager = True
            else:
                rec.is_department_manager = False

    name = fields.Many2one('hr.employee', string="Employee",
                           default=_default_employee, required=True)
    department_id = fields.Many2one('hr.department', related="name.department_id", readonly=True,
                                    string="Department")
    is_working_day = fields.Boolean(string="Working Day")
    is_holiday = fields.Boolean(string="Holiday Day")
    is_department_manager = fields.Boolean(
        string="Is Department Manager", compute="_is_department_manager")
    hour = fields.Float(string="Work Hours", required=True,
                        compute='_get_amount')
    employee_salary = fields.Float(string="Employee Salary")
    hours = fields.Integer(string="Hours", required=True)
    minute = fields.Integer(string="Minute", required=True)
    amount = fields.Float(string="Overtime Amount", compute='_get_amount')
    overtime_date = fields.Date(string="Date", required=True)
    comment = fields.Text(string="Comments")
    employee_account = fields.Many2one(
        'account.account', string="Debit Account")
    overtime_account = fields.Many2one(
        'account.account', string="Credit Account")
    analytic_debit_account_id = fields.Many2one('account.analytic.account',
                                                related='department_id.analytic_debit_account_id', readonly=True,
                                                string="Analytic Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    move_id = fields.Many2one(
        'account.move', string="Journal Entry", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('approve', 'Approved'),
        ('done', 'Done'), ('paid', 'Paid'),
        ('refuse', 'Refused'),
    ], string="State", default='draft', tracking=True, copy=False, )

    @api.depends('employee_salary', 'hour', 'minute')
    def _get_amount(self):
        for overtime in self:
            overtime.amount = 0.0
            overtime.hour = 0.0
            if overtime.employee_salary:
                hours_float = 0.0
                min = 0.0
                hour = overtime.hours
                minute = overtime.minute
                min = float(minute)/60
                hours_float = hour + min
                overtime.hour = hours_float
                overtime_hour = 0.0
                employee_hour_cost = 0.0
                employee_salary = overtime.name.contract_id.wage
                employee_basic = employee_salary * .45
                employee_cola = employee_salary * .2
                employee_hour_cost = (employee_basic + employee_cola) / 240
                if overtime.is_working_day:
                    overtime_hour = hours_float * 1.5
                if overtime.is_holiday:
                    overtime_hour = hours_float * 2
                overtime.amount = overtime_hour * employee_hour_cost

    @api.onchange('name')
    def _onchange_employee_d(self):
        if self.name:
            self.employee_salary = self.name.contract_id.wage

    # @api.model
    # def _needaction_domain_get(self):
    #     dept = self.name.user_id.has_group('is_hr_matwa.group_department_manager')
    #     hr = self.name.user_id.has_group('hr.group_hr_manager')
    #     gm = self.name.user_id.has_group('is_hr_matwa.group_hr_general_manager')
    #     account = self.name.user_id.has_group('account.group_account_manager')
    #
    #     dept_approve = dept and 'draft' or None
    #     hr_approve = hr and 'approve' or None
    #     # account_approve = account and 'confirm' or None
    #
    #     return [('state', 'in', (dept_approve, hr_approve))]

    @api.constrains('is_working_day', 'is_holiday')
    def determine_overtime_day(self):
        for rec in self:
            if not rec.is_working_day:
                if not rec.is_holiday:
                    raise UserError(
                        _("Please determine work day of overtime is it work day or holiday day!"))
            if not rec.is_holiday:
                if not rec.is_working_day:
                    raise UserError(
                        _("Please determine work day of overtime is it work day or holiday day!"))

    def department_validate(self):
        for rec in self:
            rec.state = 'approve'

    def action_sent(self):
        for rec in self:
            rec.state = 'sent'

    def hr_validate(self):
        for rec in self:
            rec.state = 'done'

    def action_paid(self):
        for rec in self:
            rec.state = 'paid'

    def unlink(self):
        if any(self.filtered(lambda hr_overtime: hr_overtime.state not in ('draft', 'refuse'))):
            raise UserError(
                _('You cannot delete a Overtime which is not draft or refused!'))
        return super(HrOvertime, self).unlink()

    import datetime

    def finance_validate(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        for overtime in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            overtime_hour = 0.0
            overtime_request_date = overtime.overtime_date
            # company_currency = overtime.name.company_id.currency_id.id
            # current_currency = self.env.user.company_id.currency_id.id
            # hour = overtime.hour
            # employee_salary = overtime.name.contract_id.wage
            # employee_basic = employee_salary*.45
            # employee_cola = employee_salary*.2
            # employee_hour_cost = (employee_basic + employee_cola)/240
            # if overtime.is_working_day:
            #     overtime_hour = hour*1.5
            #
            # if overtime.is_holiday:
            #     overtime_hour = hour*2
            # amount = overtime_hour*employee_hour_cost
            amount = overtime.amount
            overtime_name = 'Overtime For ' + overtime.name.name
            # reference = overtime_name.name
            journal_id = overtime.journal_id.id
            move_dict = {
                'narration': overtime_name,
                'ref': '/',
                'journal_id': journal_id,
                'date': overtime_request_date,
            }
            debit_line = (0, 0, {
                'name': overtime_name,
                'partner_id': False,
                'account_id': overtime.employee_account.id,
                'journal_id': journal_id,
                'date': overtime_request_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_distribution': {overtime.analytic_debit_account_id.id: 100},
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': overtime_name,
                'partner_id': False,
                'account_id': overtime.overtime_account.id,
                'journal_id': journal_id,
                'date': overtime_request_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_distribution': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_journal_credit = overtime.journal_id.default_account_id.id
                if not acc_journal_credit:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                        overtime.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_journal_credit,
                    'journal_id': journal_id,
                    'date': overtime_request_date,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_journal_deit = overtime.journal_id.default_account_id.id
                if not acc_journal_deit:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                        overtime.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_journal_deit,
                    'journal_id': journal_id,
                    'date': overtime_request_date,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            overtime.write({'move_id': move.id, 'date': overtime_request_date})
            move.action_post()
        self.state = 'done'

    def overtime_reset(self):
        for rec in self:
            rec.state = 'draft'

    def overtime_refuse(self):
        for rec in self:
            rec.state = 'refuse'

    @api.constrains('minute')
    def _minute_limit(self):
        for rec in self:
            if rec.minute >= 60:
                raise UserError(_("Please enter minutes less than 60!"))

    @api.constrains('hour')
    def _total_hour_limit(self):
        for rec in self:
            if rec.hour <= 0.0:
                raise UserError(
                    _("Overtime hours mut be greater than 0 please check it!"))


class OvertimeLine(models.Model):
    _name = 'overtime.line'
    _description = 'Overtime Line'

    name = fields.Many2one('hr.employee', string='Employee')
    employee_hour_salary = fields.Float(
        string="Hour Value", compute='compute_hour_value')
    employee_salary = fields.Float(
        string="Basic Salary", compute='compute_hour_value')
    overtime_month = fields.Float(string='Hours Total')
    overtime_month_value = fields.Float(string='Amount')
    total_work_hour = fields.Float(string='Total Normal Hour')
    total_work_overtime = fields.Float(string='Normal Hour * 1.5')
    total_holiday_hour = fields.Float(string='Total Holiday Hour')
    total_holiday_overtime = fields.Float(string='Holiday Hour * 2')
    overtime_line_id = fields.Many2one(
        'hr.overtime.month', string='Overtime Month', ondelete='cascade')

    @api.depends('name')
    def compute_hour_value(self):
        for rec in self:
            rec.employee_salary = 0.0
            rec.employee_hour_salary = 0.0
            if rec.name:
                salary = rec.name.contract_id.wage
                rec.employee_salary = salary * 0.65
                rec.employee_hour_salary = salary * 0.65 / 240


class HrOvertimeMonth(models.Model):
    _name = 'hr.overtime.month'
    _description = 'Hr Overtime Month'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Overtime')
    date_from = fields.Date(string='Date From', required=True,
                            default=time.strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
                          default=str(
                              datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                          )
    # overtime = fields.Float("Monthly Overtime", readonly=True, compute='compute_month_overtime_hours', store=True)
    overtime_line_ids = fields.One2many(
        'overtime.line', 'overtime_line_id', string='Overtime Month')
    debit_account = fields.Many2one('account.account', string="Debit Account")
    credit_account = fields.Many2one(
        'account.account', string="Credit Account")
    analytic_debit_account_id = fields.Many2one('account.analytic.account',
                                                string="Analytic Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    move_id = fields.Many2one(
        'account.move', string="Journal Entry", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Done'),
        ('refuse', 'Refused')
    ], string="State", default='draft', tracking=True, copy=False, )

    @api.onchange('date_from')
    def onchange_date(self):
        for x in self:
            ttyme = x.date_from
            locale = self.env.context.get('lang', 'en_US')
            x.name = _('Overtime for %s') % (
                tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))

    @api.depends('date_from', 'date_to')
    def compute_overtime_month(self):
        for x in self:
            ttyme = x.date_from
            locale = self.env.context.get('lang', 'en_US')
            x.name = _('Overtime for %s') % (
                tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))
            overtime_obj = x.env['hr.overtime']
            overtime_line_obj = x.env['overtime.line']
            employee_obj = x.env['hr.employee'].search([])
            x.overtime_line_ids.unlink()
            for employee in employee_obj:
                employee_id = employee.id
                overtime_ids = overtime_obj.search(
                    [('overtime_date', '>=', x.date_from), ('overtime_date', '<=', x.date_to),
                     ('name', '=', employee_id), ('state', '=', 'done')], order='name')
                total_overtime = 0.0
                sum_hours = 0.0
                sum_work_hours = 0.0
                sum_holiday_hours = 0.0
                total_amount = 0.0
                overtime_holiday = 0.0
                overtime_working = 0.0
                total_work_overtime = 0.0
                total_holiday_overtime = 0.0
                total_hours = 0.0
                for overtime in overtime_ids:
                    # employee = overtime.name.id
                    basic_salary = employee.contract_id.wage * 0.65
                    employee_salary_hour = basic_salary / 240
                    if overtime.is_working_day:
                        sum_work_hours += overtime.hour
                    if overtime.is_holiday:
                        sum_holiday_hours += overtime.hour
                    total_work_overtime = sum_work_hours * 1.5
                    total_holiday_overtime = sum_holiday_hours * 2
                    total_hours = total_work_overtime + total_holiday_overtime
                    total_amount = total_hours * employee_salary_hour
                    # if sum_hours != 0.0:
                    #     if overtime.is_working_day:
                    #         overtime_working = sum_hours * employee_salary_hour * 1.5
                    #     if overtime.is_holiday:
                    #         overtime_holiday = sum_hours * employee_salary_hour * 2
                    #     total_overtime = overtime_working + overtime_holiday
                if total_hours != 0.0:
                    overtime_line_ids = overtime_line_obj.create({
                        'name': employee_id,
                        'total_work_hour': sum_work_hours,
                        'total_work_overtime': total_work_overtime,
                        'total_holiday_hour': sum_holiday_hours,
                        'total_holiday_overtime': total_holiday_overtime,
                        'overtime_month': total_hours,
                        'overtime_month_value': total_amount,
                        'overtime_line_id': x.id})
        return True

    def confirm_overtime(self):
        for rec in self:
            rec.state = 'confirm'

    def finance_validate(self):
        for rec in self:
            precision = self.env['decimal.precision'].precision_get('Payroll')
            move_obj = self.env['account.move']
            move_line_obj = self.env['account.move.line']
            currency_obj = self.env['res.currency']
            created_move_ids = []
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            overtime_hour = 0.0
            amount = 0.0
            overtime_request_date = datetime.now()
            for line in rec.overtime_line_ids:
                amount += line.overtime_month_value
                # company_currency = overtime.name.company_id.currency_id.id
                # current_currency = self.env.user.company_id.currency_id.id
                # hour = overtime.hour
                # employee_salary = overtime.name.contract_id.wage
                # employee_basic = employee_salary*.45
                # employee_cola = employee_salary*.2
                # employee_hour_cost = (employee_basic + employee_cola)/240
                # if overtime.is_working_day:
                #     overtime_hour = hour*1.5
                #
                # if overtime.is_holiday:
                #     overtime_hour = hour*2
                # amount = overtime_hour*employee_hour_cost
                # amount = overtime.amount
                overtime_name = 'Overtime For ' + rec.name
                # reference = overtime_name.name
                journal_id = rec.journal_id.id
                move_dict = {
                    'narration': overtime_name,
                    'ref': '/',
                    'journal_id': journal_id,
                    'date': overtime_request_date,
                }
                debit_line = (0, 0, {
                    'name': overtime_name,
                    'partner_id': line.employee_id.related_partner_id.id,
                    'account_id': rec.debit_account.id,
                    'journal_id': journal_id,
                    'date': overtime_request_date,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'analytic_distribution': {rec.analytic_debit_account_id.id: 100},
                    'tax_line_id': 0.0,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
                credit_line = (0, 0, {
                    'name': overtime_name,
                    'partner_id': line.employee_id.related_partner_id.id,
                    'account_id': rec.credit_account.id,
                    'journal_id': journal_id,
                    'date': overtime_request_date,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'analytic_distribution': False,
                    'tax_line_id': 0.0,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - \
                    credit_line[2]['debit']
                if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                    acc_journal_credit = rec.journal_id.default_account_id.id
                    if not acc_journal_credit:
                        raise UserError(
                            _('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                rec.journal_id.name))
                    adjust_credit = (0, 0, {
                        'name': _('Adjustment Entry'),
                        'partner_id': line.employee_id.related_partner_id.id,
                        'account_id': acc_journal_credit,
                        'journal_id': journal_id,
                        'date': overtime_request_date,
                        'debit': 0.0,
                        'credit': debit_sum - credit_sum,
                    })
                    line_ids.append(adjust_credit)

                elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                    acc_journal_deit = rec.journal_id.default_account_id.id
                    if not acc_journal_deit:
                        raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                            rec.journal_id.name))
                    adjust_debit = (0, 0, {
                        'name': _('Adjustment Entry'),
                        'partner_id': False,
                        'account_id': acc_journal_deit,
                        'journal_id': journal_id,
                        'date': overtime_request_date,
                        'debit': credit_sum - debit_sum,
                        'credit': 0.0,
                    })
                    line_ids.append(adjust_debit)
                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                rec.write({'move_id': move.id})
                move.action_post()
                for line in rec.overtime_line_ids:
                    overtime_obj = self.env['hr.overtime']
                    overtime_ids = overtime_obj.search(
                        [('overtime_date', '>=', self.date_from), ('overtime_date', '<=', self.date_to),
                         ('name', '=', line.name.id), ('state', '=', 'done')], order='name')
                    for pay in overtime_ids:
                        pay.action_paid()
            rec.state = 'done'

    def unlink(self):
        if any(self.filtered(lambda overtime_month: overtime_month.state not in ('draft', 'refuse'))):
            raise UserError(
                _('You cannot delete a Overtime which is not draft or refused!'))
        return super(HrOvertimeMonth, self).unlink()

        # @api.depends('date_from','date_to')
        # def compute_month_overtime_hours(self):
        #     sum_hours = 0.0
        #     employee = False
        #     for x in self:
        #         employee_salary = x.contract_id.wage
        #         employee_salary_hour = employee_salary / 240
        #         # overtime = self.env['hr.overtime']
        #         overtime_id = x.env['hr.overtime']
        #         overtime_ids = x.search([ ('overtime_date', '>=', x.date_from),('overtime_date', '<=', x.date_to)], order='name')
        #         for overtime in overtime_ids:
        #             employee_id = overtime.name.id
        #             if employee == employee_id:
        #                 # overtime_ids = {''}
        #                 sum_hours += overtime.hour
        #                 if overtime_ids.is_working_day:
        #                     self.overtime = sum_hours * employee_salary_hour * 1.5
        #                     self.overtime_line_ids  =  overtime_ids.overtime_line_id
        #                 if overtime_ids.is_holiday:
        #                     self.overtime = sum_hours * employee_salary_hour * 2
        #                     self.overtime_line_ids = overtime_ids.overtime_line_id
        # line_id = overtime_id.create({
        #     'paid_date': date_start_str,
        #     'paid_amount': round(amount_per_time, 2),
        #     'employee_id': loan.employee_id.id,
        #     'loan_id': loan.id})


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    overtime_id = fields.Many2one('hr.overtime', string="Overtime")


class overtime_emp(models.Model):
    _name = "overtime.emp"
    _description = 'Overtime Emp'
    _rec_name = "date"

    # name = fields.Char("Name")
    date = fields.Date("Date")
    emp_ids = fields.One2many("overtime.emp.list", "work_id", "Employees")
    requested = fields.Boolean("Requested")

    # @api.model
    def create_overtime_req(self):
        today_date = datetime.now().date()
        emp_ids = self.env['overtime.emp'].search([('date', '=', today_date)])
        for emp in emp_ids:
            for employee_id in emp.emp_ids:
                attendance = self.env['hr.attendance'].search(
                    [('employee_id', '=', employee_id.emp_id.id) and ('check_in_date', '=', today_date)])
                if attendance.worked_hours > 8:
                    overtime_hours = attendance.worked_hours - 8
                    if not self.requested:
                        rec_vals = {
                            'name': employee_id.emp_id.id,
                            'overtime_date': self.date,
                            'is_working_day': True,
                            'minute': 0,
                            'hours': overtime_hours,
                            'hour': overtime_hours,
                        }
                        emp_overtime = self.env['hr.overtime'].create(rec_vals)
                        self.requested = True


class overtime_emp_list(models.Model):
    _name = "overtime.emp.list"
    _description = 'Overtime Emp List'

    work_id = fields.Many2one("overtime.emp")
    emp_id = fields.Many2one("hr.employee", "Employee")
    dept_id = fields.Many2one("hr.department", "Department")
