# ﻿!/usr/bin/env python
# -*- coding: utf-8 -*-
# ###########

from odoo import fields, models, _
import xlsxwriter
import base64
from io import BytesIO
from datetime import datetime
from odoo.exceptions import UserError
from dateutil import relativedelta


class WizardLtaTransport(models.Model):
    _name = 'wizard.lta.transport'
    _description = 'Print ALW'

    from_date = fields.Date(string='Date From', required=True)
    # , default = time.strftime('%Y-%m-01')
    to_date = fields.Date(string='Date To', required=True,
                          default=str(
                              datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                          )
    name = fields.Char(string="LTA & Transport Allowance")

    def print_report(self):
        for report in self:
            overtime_ids = False
            from_date = report.from_date
            to_date = report.to_date
            if self.from_date > self.to_date:
                raise UserError(
                    _("You must be enter start date less than end date !"))
            report.name = 'LTA & Transport From ' + \
                str(from_date) + ' To ' + str(to_date)
            report_title = 'Transport Allowance From ' + \
                str(from_date) + ' To ' + str(to_date)
            report_lta_title = 'LTA Allowance From ' + \
                str(from_date) + ' To ' + str(to_date)
            file_name = _('LTA and Transport.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet_transport = workbook.add_worksheet('Transport')
            excel_sheet_lta = workbook.add_worksheet('LTA')
            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'border': 1})
            footer_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'border': 0})
            footer2_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'border': 0})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            header_format.set_align('center')
            header_format.set_text_wrap()
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white'})
            title_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            title_format.set_align('center')
            format.set_align('center')
            header_format_sequence.set_align('left')
            format.set_text_wrap()
            format.set_num_format('#,##0.00')
            format_details = workbook.add_format()
            format_details.set_num_format('#,##0.00')
            transport_lta_ids = report.env['lta.transport.line'].search(
                [('date', '<=', to_date), ('date', '>=', from_date)])
            sequence_id = 0
            col = 0
            row = 5
            first_row = 6
            excel_sheet_transport.set_column(0, 0, 8)
            excel_sheet_transport.write(row, col, 'S', header_format)
            excel_sheet_lta.write(row, col, 'S', header_format)
            col += 1
            excel_sheet_transport.set_column(1, 1, 15)
            excel_sheet_lta.set_column(1, 1, 15)
            excel_sheet_transport.write(row, col, 'Code', header_format)
            excel_sheet_lta.write(row, col, 'Code', header_format)
            col += 1
            excel_sheet_transport.set_column(2, 2, 20)
            excel_sheet_lta.set_column(2, 2, 20)
            excel_sheet_transport.write(row, col, 'Name', header_format)
            excel_sheet_lta.write(row, col, 'Name', header_format)
            col += 1
            excel_sheet_transport.set_column(3, 4, 25)
            excel_sheet_lta.set_column(3, 4, 25)
            excel_sheet_transport.write(row, col, 'Department', header_format)
            excel_sheet_lta.write(row, col, 'Department', header_format)
            col += 1
            excel_sheet_transport.write(row, col, 'Job Title ', header_format)
            excel_sheet_lta.write(row, col, 'Job Title ', header_format)
            col += 1
            excel_sheet_transport.set_column(5, 7, 15)
            excel_sheet_lta.set_column(5, 7, 15)
            excel_sheet_transport.write(row, col, 'Transport', header_format)
            excel_sheet_lta.write(row, col, 'LTA', header_format)
            col += 1
            excel_sheet_transport.write(row, col, 'Deduct', header_format)
            col += 1
            excel_sheet_transport.write(
                row, col, 'Transport After Deduct', header_format)
            excel_sheet_transport.merge_range(
                0, 0, 1, 7, 'MTWA International Investment Co.LTD', title_format)
            excel_sheet_transport.merge_range(
                2, 0, 3, 7, report_title, title_format)
            excel_sheet_lta.merge_range(
                0, 0, 1, 7, 'MTWA International Investment Co.LTD', title_format)
            excel_sheet_lta.merge_range(
                2, 0, 3, 7, report_lta_title, title_format)
            excel_sheet_transport.merge_range(3, 0, 4, 7, '', format)
            excel_sheet_lta.merge_range(3, 0, 4, 7, '', format)

            excel_sheet_transport.cols_left_to_right = 1
            total_transport_allowance = 0.0
            total_deduction = 0.0
            total = 0.0
            employee_id = False
            department = False
            job = False
            code = False
            sequence_lta = 0
            excel_sheet_lta.set_column(0, 0, 8)
            excel_sheet_lta.cols_left_to_right = 1
            total_lta = 0.0
            if transport_lta_ids:
                for transport_lta_id in transport_lta_ids:
                    col = 0
                    col = 0
                    row += 1
                    sequence_id += 1
                    employee_id = transport_lta_id.employee_id.name
                    code = transport_lta_id.employee_id.code
                    department = transport_lta_id.department_id.name
                    job = transport_lta_id.job_id.name
                    transport_allowance = transport_lta_id.transport_allowance
                    lta_allowance = transport_lta_id.lta_allowance
                    deduction = transport_lta_id.deduction
                    total_transport_allowance += transport_allowance
                    total_deduction += deduction
                    total_lta += lta_allowance
                    total_transport = transport_allowance - deduction
                    excel_sheet_transport.write(
                        row, col, sequence_id, header_format_sequence)
                    excel_sheet_lta.write(
                        row, col, sequence_id, header_format_sequence)
                    col += 1
                    if code:
                        excel_sheet_transport.write(
                            row, col, code, header_format_sequence)
                        excel_sheet_lta.write(
                            row, col, code, header_format_sequence)
                    else:
                        excel_sheet_transport.write(
                            row, col, '', header_format_sequence)
                        excel_sheet_lta.write(
                            row, col, '', header_format_sequence)
                    col += 1
                    if employee_id:
                        excel_sheet_transport.write(
                            row, col, employee_id, header_format_sequence)
                        excel_sheet_lta.write(
                            row, col, employee_id, header_format_sequence)
                    else:
                        excel_sheet_transport.write(
                            row, col, '', header_format_sequence)
                        excel_sheet_lta.write(
                            row, col, '', header_format_sequence)

                    col += 1
                    if department:
                        excel_sheet_transport.write(
                            row, col, department, header_format_sequence)
                        excel_sheet_lta.write(
                            row, col, department, header_format_sequence)
                    else:
                        excel_sheet_transport.write(
                            row, col, '', header_format_sequence)
                        excel_sheet_lta.write(
                            row, col, '', header_format_sequence)
                    col += 1
                    if job:
                        excel_sheet_transport.write(
                            row, col, job, header_format_sequence)
                        excel_sheet_lta.write(
                            row, col, job, header_format_sequence)
                    else:
                        excel_sheet_transport.write(
                            row, col, '', header_format_sequence)
                        excel_sheet_lta.write(
                            row, col, '', header_format_sequence)
                    col += 1
                    if transport_allowance:
                        excel_sheet_transport.write(
                            row, col, transport_allowance, header_format_sequence)
                        total_transport_allowance += transport_allowance
                    else:
                        excel_sheet_transport.write(
                            row, col, 0.0, header_format_sequence)
                    if lta_allowance:
                        excel_sheet_lta.write(
                            row, col, lta_allowance, header_format_sequence)
                        total_lta += lta_allowance
                    else:
                        excel_sheet_lta.write(
                            row, col, 0.0, header_format_sequence)
                    col += 1
                    if deduction:
                        excel_sheet_transport.write(
                            row, col, deduction, header_format_sequence)
                        total_deduction += deduction
                    else:
                        excel_sheet_transport.write(
                            row, col, 0.0, header_format_sequence)
                    col += 1
                    if total_transport:
                        excel_sheet_transport.write(
                            row, col, total_transport, header_format_sequence)
                    else:
                        excel_sheet_transport.write(
                            row, col, 0.0, header_format_sequence)
                    # total += lta_allowance

            col = 0
            row += 1
            excel_sheet_transport.merge_range(
                row, col, row, col + 4, 'Total', header_format)
            excel_sheet_transport.write_formula(
                row, 5, 'SUM(f' + str(first_row + 1) + ':f' + str(row) + ')', header_format)
            excel_sheet_transport.write_formula(row, 6, 'SUM(g' + str(first_row + 1) + ':g' + str(row) + ')',
                                                header_format)
            excel_sheet_transport.write_formula(row, 7, 'SUM(h' + str(first_row + 1) + ':h' + str(row) + ')',
                                                header_format)
            excel_sheet_lta.merge_range(
                row, col, row, col + 4, 'Total', header_format)
            excel_sheet_lta.write_formula(
                row, 5, 'SUM(f' + str(first_row + 1) + ':f' + str(row) + ')', header_format)
            footer_format.set_underline()
            excel_sheet_lta.write(
                row+2, col + 2, 'Prepared by:', footer_format)
            excel_sheet_transport.write(
                row+2, col + 2, 'Prepared by:', footer_format)
            footer2_format.set_text_wrap()
            excel_sheet_transport.write(
                row+3, col + 2, report.create_uid.name, footer2_format)
            excel_sheet_lta.write(
                row+3, col + 2, report.create_uid.name, footer2_format)
            excel_sheet_transport.write(
                row+4, col + 2, 'HR & Admin Manager', footer2_format)
            excel_sheet_lta.write(
                row+4, col + 2, 'HR & Admin Manager', footer2_format)
            excel_sheet_transport.write(
                row+4, col + 6, 'Finance & Accounting Manager', footer2_format)
            workbook.close()
            file_download = base64.b64encode(fp.getvalue())
            fp.close()
            wizard_model = self.env['lta.transport.excel']
            res_id = wizard_model.create(
                {'name': file_name, 'file_download': file_download})
            return {
                'name': 'Files to Download',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'lta.transport.excel',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': res_id.id,
            }


############################################


class LtaTransportReportExcel(models.TransientModel):
    _name = 'lta.transport.excel'
    _description = 'Lta Transport Excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
