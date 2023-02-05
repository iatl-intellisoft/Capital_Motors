# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, _
from odoo.exceptions import UserError


class LtaTransportEmployees(models.TransientModel):
    _name = 'lta.transport.employees'
    _description = 'Generate Leave bonus and transport allowance for all selected employees'

    employee_ids = fields.Many2many(
        'hr.employee', 'lta_transport_group_rel', 'lta_transport_id', 'employee_id', 'Employees')

    def compute_grant_sheet(self):
        for rec in self:
            grants = rec.env['lta.transport.line']
            self.env['lta.transport'].lta_transport_ids.unlink()
            [data] = self.read()
            active_id = rec.env.context.get('active_id')
            if active_id:
                [run_data] = rec.env['lta.transport'].browse(
                    active_id).read(['name'])
            name = run_data.get('name')
            date = run_data.get('date')
            if not data['employee_ids']:
                raise UserError(
                    _("You must select employee(s) to generate allowance(s)."))
            for employee in rec.env['hr.employee'].browse(data['employee_ids']):
                allowance_name = 'Transport and LTA allowance for ' + employee.name + ' ' + name
                lta_transport_ids = []
                leave_bonus = employee.contract_id.wage * 6 / 12
                res = {
                    'employee_id': employee.id,
                    'name': allowance_name,
                    'contract_id': employee.contract_id,
                    'department_id': employee.department_id,
                    'job_id': employee.job_id,
                    'transport_allowance': employee.contract_id.transport_allowance,
                    'lta_allowance': leave_bonus,
                    'lta_transport_id': active_id,

                }
                # grants.grant_ids.unlink()
                grants += self.env['lta.transport.line'].create(res)
        return {'type': 'ir.actions.act_window_close'}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
