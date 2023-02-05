from odoo import api, fields, models, _
from datetime import datetime
from odoo.osv import expression


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    analytic_debit_account_id = fields.Many2one(
        'account.analytic.account', string="Department Analytic Account")


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _order = 'code'

    code = fields.Char(string='ID No.', index=True, )
    hiring_date = fields.Date(string="Hiring  Date")
    age = fields.Char(compute='_calculate_age', string='Age')
    bank_acc = fields.Char("Bank Account")
    related_partner_id = fields.Many2one('res.partner', "Related Partner")

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "Code Already Exists !"),
    ]

    @api.model
    def default_get(self, fields):
        res = super(HrEmployee, self).default_get(fields)
        next_seq = self.env['ir.sequence'].next_by_code('student.unino.sequence')
        res.update({'code': next_seq})
        return res

    # Employee Code
    @api.model_create_multi
    def create(self, vals_list):
        res = super(HrEmployee, self).create(vals_list)
        next_seq = self.env['ir.sequence'].next_by_code('hr.employee')
        res.update({'code': next_seq})
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(
                ' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.depends('birthday')
    def _calculate_age(self):
        str_now = datetime.now().date()
        age = ''
        employee_years = 0
        for employee in self:
            if employee.birthday:
                date_start = datetime.strptime(
                    str(employee.birthday), '%Y-%m-%d').date()
                total_days = (str_now - date_start).days
                employee_years = int(total_days / 365)
                remaining_days = total_days - 365 * employee_years
                employee_months = int(12 * remaining_days / 365)
                employee_days = int(0.5 + remaining_days -
                                    365 * employee_months / 12)
                age = str(employee_years) + ' Year(s) ' + str(employee_months) + ' Month(s) ' + str(
                    employee_days) + ' day(s)'
            employee.age = age
            #TODO employee.age_in_years = employee_years
