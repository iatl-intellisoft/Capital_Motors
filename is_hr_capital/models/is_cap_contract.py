# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    def get_default_currency(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id.id

    wage = fields.Monetary(string='Gross Salary', tracking=True)
    currency_id = fields.Many2one(
        string="Currency", default=get_default_currency, readonly=False)
    basic = fields.Monetary(string='Basic Salary', tracking=True)
    cola_allowance = fields.Monetary(
        string='Cola', tracking=True)
    housing_allowance = fields.Monetary(
        string='Housing Allowance', tracking=True)
    transportation_allowance = fields.Monetary(
        string='Transportation Allowance', tracking=True)

    income_tax = fields.Boolean(string='Personal Income Tax', default=True)
    social_insurance = fields.Boolean(string='Social Insurance', default=False)
    social_insurance_type = fields.Selection([('amount', 'Fixed Amount'), ('percentage', 'Percentage 8%'),
                                              ], string='Social Insurance Type', tracking=True)
    insurance_amount = fields.Monetary(
        string='Insurance Amount', tracking=True)
    insurance_amount_Percentage = fields.Monetary(
        string='8 % Percentage Amount From', tracking=True)
    medical_deduction = fields.Monetary(
        string='Medical Deduction', tracking=True)
    phone = fields.Monetary(string='Phone', default=True)
    under_training = fields.Boolean("Under Training")
    official_sal = fields.Monetary(
        string="Official Salary", compute="computeOfficialSalary", store=True)
    official_sal_per = fields.Monetary(string="Official Salary %")
    payment_type = fields.Selection([('bank', 'Bank'), ('cash', 'Cash'),
                                     ], string='Payment Type', tracking=True)

    @api.depends('wage', 'official_sal_per')
    def computeOfficialSalary(self):
        for rec in self:
            rec.official_sal = rec.official_sal_per / 100 * rec.wage

    @api.onchange('wage')
    def compute_basic(self):
        for rec in self:
            if rec.wage > 0:
                num = self.env['payroll.calculation'].search(
                    [], order='id DESC', limit=1).employee_basic
                rec.basic = rec.wage * num / 100
                num = self.env['payroll.calculation'].search(
                    [], order='id DESC', limit=1).cola
                rec.cola_allowance = rec.wage * num / 100
                num = self.env['payroll.calculation'].search(
                    [], order='id DESC', limit=1).housing
                rec.housing_allowance = rec.wage * num / 100
                num = self.env['payroll.calculation'].search(
                    [], order='id DESC', limit=1).transportation
                rec.transportation_allowance = rec.wage * num / 100
                num = self.env['payroll.calculation'].search(
                    [], order='id DESC', limit=1).official_Sal
                rec.official_sal_per = rec.wage * num / 100
            else:
                rec.basic = 0
                rec.cola_allowance = 0
                rec.housing_allowance = 0
                rec.transportation_allowance = 0
