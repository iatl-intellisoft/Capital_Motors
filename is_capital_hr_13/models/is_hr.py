# -*- coding: utf-8 -*-
###########

import datetime
from odoo import api, fields, models, _


class hr_applicant(models.Model):
    _inherit = 'hr.applicant'

    is_training = fields.Boolean("Is Training")
    date_of_app = fields.Date("Date")
    city = fields.Char("City")
    country = fields.Many2one("res.country", "Country")
    availability = fields.Date("Date Available")
    worked_here = fields.Selection(string="Have you ever worked for this company?",
                                   selection=[('yes', "Yes"), ('no', "No")])
    if_yes_when = fields.Char("If so, when?")

    high_school = fields.Char("High School")
    school_add = fields.Char("Address")
    school_from = fields.Date("From")
    school_to = fields.Date("To")
    college = fields.Char("College")
    college_add = fields.Char("Address")
    college_from = fields.Date("From")
    college_to = fields.Date("To")
    other = fields.Char("Other")
    other_add = fields.Char("Address")
    other_from = fields.Date("From")
    other_to = fields.Date("To")

    ref_one = fields.Char("Full Name")
    ref_one_relation = fields.Char("Relationship")
    ref_one_ph = fields.Char("Phone")
    ref_one_com = fields.Char("Company")
    ref_one_add = fields.Char("Address")

    ref_two = fields.Char("Full Name")
    ref_two_relation = fields.Char("Relationship")
    ref_two_ph = fields.Char("Phone")
    ref_two_com = fields.Char("Company")
    ref_two_add = fields.Char("Address")

    ref_three = fields.Char("Full Name")
    ref_three_relation = fields.Char("Relationship")
    ref_three_ph = fields.Char("Phone")
    ref_three_com = fields.Char("Company")
    ref_three_add = fields.Char("Address")

    comp_one = fields.Char("Company")
    comp_one_ph = fields.Char("Phone")
    comp_one_add = fields.Char("Address")
    comp_one_sup = fields.Char("Supervisor")
    comp_one_jop = fields.Char("Job Title")
    comp_one_str = fields.Char("Starting Salary")
    comp_one_end = fields.Char("Ending Salary")
    comp_one_resp = fields.Text("Responsibilities")
    comp_one_from = fields.Date("From")
    comp_one_to = fields.Date("To")
    comp_one_reson = fields.Text("Reason for Leaving")
    comp_one_reson = fields.Selection(string="May we contact your previous supervisor for a reference?",
                                      selection=[('yes', "Yes"), ('no', "No")])

    comp_two = fields.Char("Company")
    comp_two_ph = fields.Char("phone")
    comp_two_add = fields.Char("Address")
    comp_two_sup = fields.Char("Supervisor")
    comp_two_jop = fields.Char("Job Title")
    comp_two_str = fields.Char("Starting Salary")
    comp_two_end = fields.Char("Ending Salary")
    comp_two_resp = fields.Text("Responsibilities")
    comp_two_from = fields.Date("From")
    comp_two_to = fields.Date("To")
    comp_two_reson = fields.Text("Reason for Leaving")
    comp_two_reson = fields.Selection(string="May we contact your previous supervisor for a reference?",
                                      selection=[('yes', "Yes"), ('no', "No")])

    comp_three = fields.Char("Company")
    comp_three_ph = fields.Char("phone")
    comp_three_add = fields.Char("Address")
    comp_three_sup = fields.Char("Supervisor")
    comp_three_jop = fields.Char("Job Title")
    comp_three_str = fields.Char("Starting Salary")
    comp_three_end = fields.Char("Ending Salary")
    comp_three_resp = fields.Text("Responsibilities")
    comp_three_from = fields.Date("From")
    comp_three_to = fields.Date("To")
    comp_three_reson = fields.Text("Reason for Leaving")
    comp_three_reson = fields.Selection(selection=[('yes', "Yes"), ('no', "No")],
                                        string="May we contact your previous supervisor for a reference?")


class emp_support(models.Model):
    _name = "emp.support"
    _description = "Employee Support"
    _rec_name = "item"

    emp_name = fields.Many2one("res.users", string="Sales Person")
    customer = fields.Many2one("res.partner", "Customer")
    date = fields.Date("Date")
    item = fields.Char('Item')
    amount = fields.Float("Amount")
    debit_account = fields.Many2one('account.account', string="Debit Account")
    credit_account = fields.Many2one('account.account', string="Credit Account")
    journal_id = fields.Many2one('account.journal', 'Bank/Cash Journal',
                                 help='Payment journal.',
                                 domain=[('type', 'in', ['bank', 'cash'])])

    @api.model
    def create(self, vals):
        res = super(emp_support, self).create(vals)
        debit_line_vals = {
            'name': res.item,
            'debit': res.amount,
            'credit': 0.0,
            'account_id': res.debit_account.id,
        }
        credit_line_vals = {
            'name': res.item,
            'debit': 0.0,
            'credit': res.amount,
            'account_id': res.credit_account.id,
        }
        line_ids = [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
        move_vals = {
            'date': res.date,
            'journal_id': res.journal_id.id,
            'line_ids': line_ids,
        }
        move = self.env['account.move'].create(move_vals)
        return res


class office_maintenance(models.Model):
    _name = "office.maintenance"
    _description = 'Office Maintenance'
    _rec_name = "maintenance_to"

    req = fields.Many2one("res.users", "Requester")
    amount = fields.Float("Amount")
    maintenance_to = fields.Char("Maintenance To")
    date = fields.Date("Date")

    @api.model
    def create(self, vals):
        res = super(office_maintenance, self).create(vals)
        rec_vals = {
            'fa_date': res.date,
            'request_amount': res.amount,
            'reason': res.maintenance_to,
            'state': "draft",
            'reason': "",
        }
        finance_approval = self.env['finance.approval'].create(rec_vals)
        return res


class HR_attendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_date = fields.Date("Date", compute='check_in_without_time',store=True)

    def check_in_without_time(self):
        for rec in self:
            rec.check_in_date = rec.check_in.date()
            # print(rec.check_in_date,'khansaaaaaaaaaaa')


class saturday_work(models.Model):
    _name = "saturday.work"
    _description = "Saturday Work"
    _rec_name = "date"

    # name = fields.Char("Name")
    date = fields.Date("Date")
    emp_ids = fields.One2many("hr.emp", "work_id", "Employees")

    @api.model
    def create_penalty(self):
        today_date = datetime.now().date()
        print(today_date, 'today_date')
        saturday_work_ids = self.env['saturday.work'].search([('date', '=', today_date)])
        for saturday_work_id in saturday_work_ids:
            for employee_id in saturday_work_id.emp_ids:
                print(employee_id.emp_id.id, 'here we are')
                attendance = self.env['hr.attendance'].search(
                    [('check_in_date', '=', today_date) and ('employee_id', '=', employee_id.emp_id.id)])
                if not attendance:
                    rec_vals = {
                        'employee_id': employee_id.id,
                        'description': 'absent in Saturday work plan ',
                    }
                    emp_penalty = self.env['hr.emp.penalty'].create(rec_vals)


class hr_emp(models.Model):
    _name = "hr.emp"
    _description = 'HR Employee'

    work_id = fields.Many2one("saturday.work")
    emp_id = fields.Many2one("hr.employee", "Employee")
    dept_id = fields.Many2one("hr.department", "Department")


class hr_con(models.Model):
    _inherit = 'hr.contract'

    contract_period = fields.Float("contract period", digits=(16, 4), compute='compute_contract_period')

    def compute_contract_period(self):
        for rec in self:
            print('here we are')
            contract_period = 0.0
            contract_period = str((datetime.strptime(rec.date_start) - datetime.strptime(rec.date_end)).days)
            rec.contract_period = contract_period
