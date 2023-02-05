# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from odoo import models, fields


class Create_penalties(models.TransientModel):
    _name = "hr.penalties"
    _description = 'Hr Penalties'

    def Create_penalty(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        for rec in self.env['hr.attendance'].browse(active_ids):
            penalty_amount = 0
            violation_id = 0
            no_minute = rec.check_in.minute
            today_date = datetime.now().date()
            minutes = self.env['hr.violation.type'].search(
                [('deduction_type', '=', 'minutes')])
            hour = self.env['hr.violation.type'].search(
                [('deduction_type', '=', 'hour')])
            day = self.env['hr.violation.type'].search(
                [('name', '=', 'Day')])
            # if rec.id:
            violation_id = minutes.id
            # attendance = self.env['hr.attendance'].search(
            #     [('check_in_date', '=', today_date) and ('employee_id', '=', rec.employee_id.id)])
            # if not attendance:
            #     violation_id = day.id
            if no_minute > 15:
                rec_vals = {
                    'employee_id': rec.employee_id.id,
                    'violation_id': violation_id,
                    'description': "Attendance Penalties",
                    'penalty_type': "attention",
                    'penalty_amount': no_minute - 15,
                    'state': "draft",
                }
                emp_penalty = self.env['hr.emp.penalty'].create(rec_vals)
