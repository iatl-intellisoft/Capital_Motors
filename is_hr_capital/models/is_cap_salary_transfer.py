import base64

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _


class SalaryTransfer(models.Model):
    _name = 'salary.transfer'
    _description = 'Salary Transfer'
    _order = 'date_end desc'

    name = fields.Char(required=True, readonly=True, states={
                       'draft': [('readonly', False)]})
    # slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips', readonly=True,
    #     states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verify'),
        ('close', 'Done'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(string='Date From', required=True, readonly=True,
                             states={'draft': [('readonly', False)]}, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True, readonly=True,
                           states={'draft': [('readonly', False)]},
                           default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_close(self):
        self.write({'state': 'close'})

    def action_open_payslips(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.slip_ids.ids]],
            "name": "Payslips",
        }
