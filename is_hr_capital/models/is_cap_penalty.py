##############################################################################
#    Description: Ratification Customization                                        #
#    Author: IntelliSoft Software                                            #
#    Date: Dec 2017 -  Till Now                                              #
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrViolationType(models.Model):
    _name = 'hr.violation.type'
    _description = 'Violation Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True, translate=True)
    deduction_type = fields.Selection(
        [('day', 'Day'), ('hour', 'hour'), ('minutes', 'Minutes')])
    penalty = fields.Integer('Penalty')


# violation and penalty
class HrEmpPenalty(models.Model):
    _name = 'hr.emp.penalty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Penalty'

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char('No', readonly=True)
    user_id = fields.Many2one(
        'res.users', 'Ordered by', readonly=True, default=lambda self: self.env.user)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, default=_default_employee)
    date = fields.Date("Date", default=fields.Date.today())
    department_id = fields.Many2one(
        'hr.department', 'Department', related="employee_id.department_id", readonly=True)
    job_id = fields.Many2one(
        'hr.job', readonly=True, string="Job Position", related="employee_id.job_id")
    violation_id = fields.Many2one('hr.violation.type', 'Violation')
    penalty = fields.Integer('Penalty', related="violation_id.penalty")
    description = fields.Text("Reasons")
    penalty_type = fields.Selection([('attention', 'Attention Notice'), ('first written', 'First Warning'),
                                     ('second written', 'Second Warning'),
                                     ('warning', 'Written Warning')], 'Penalty Type')
    dmanager_id = fields.Many2one(
        'res.users', 'Department Manager', readonly=True)
    hr_manager_id = fields.Many2one('res.users', 'Hr Manager', readonly=True)
    hrg_manager_id = fields.Many2one(
        'res.users', 'Hr General Manager', readonly=True)
    dnote = fields.Char('Department Manager Comment')
    hrnote = fields.Char('Hr Manager Comment')
    hrgnote = fields.Char('Hr General Manager Comment')
    penalty_amount = fields.Float("Number", required=True)

    state = fields.Selection(
        [('draft', 'Clarification'), ('clarification', 'Department Manager Approved'), ('dm', 'Hr Manager Approved'), ('hr', 'Approved'),
         ('done', 'Done'), ('refuse', 'Refused')],
        'Status', readonly=True, tracking=True, copy=False, default='draft')

    # overriding default get
    @api.model
    def default_get(self, fields):
        res = super(HrEmpPenalty, self).default_get(fields)
        next_seq = self.env['ir.sequence'].get('penalty.no')
        res.update({'name': next_seq, })
        return res

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(
                    _('You are not allow to delete the Confirm and Done state records'))
        res = super(HrEmpPenalty, self).unlink()
        return res

    def clarification(self):
        for rec in self:
            rec.state = 'clarification'

    def dm(self):
        for rec in self:
            rec.dmanager_id = rec.env.uid
            rec.state = 'dm'

    def hr(self):
        for rec in self:
            rec.hr_manager_id = self.env.uid
            rec.state = 'hr'

    def hrg(self):
        for rec in self:
            rec.hrg_manager_id = self.env.uid
            rec.state = 'done'

    def refuse(self):
        for rec in self:
            rec.state = 'refuse'
