# -*- coding: utf-8 -*-

from odoo import models, fields


class OvertimeSetting(models.Model):
    _name = 'overtime.setting'
    _description = 'Overtime Setting'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='Overtime Setting',
                       string='Reference', readonly=1)
    normal_hours = fields.Float(
        string='Normal Hours', default=1.5, required=True, tracking=True)
    holiday_hours = fields.Float(
        string='Holiday Hours', default=2, required=True, tracking=True)
    days_employee = fields.Integer(
        string='Divide Employee Salary By', default=240, tracking=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Overtime Setting Already Exists !"),
    ]


class PayrollCalculation(models.Model):
    _name = 'payroll.calculation'
    _description = 'Payroll Calculation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='Payroll Calculation',
                       string='Reference', readonly=1)
    employee_basic = fields.Float(
        string='Basic', default=48, tracking=True)
    cola = fields.Float(string=' Cola', default=20,
                        tracking=True)
    housing = fields.Float(string=' Housing', default=14,
                           tracking=True)
    transportation = fields.Float(
        string='Transportation', default=18, tracking=True)
    official_Sal = fields.Float(
        string='Official Salary %', default=50, tracking=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Payroll Calculation Setting Already Exists !"),
    ]
