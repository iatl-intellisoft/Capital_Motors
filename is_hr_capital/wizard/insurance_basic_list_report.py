# -*- coding: utf-8 -*-
###########

from odoo import api, fields, models, _
import xlsxwriter
import base64
from io import BytesIO
from datetime import datetime


class InsuranceBasicList(models.Model):
    _name = 'insurance.basic.list'
    _description = 'Print Insurance Basic List details'

    date_from = fields.Date('Date From/Hiring')
    date_to = fields.Date('Date To', default=fields.Date.today())
    emp_id = fields.Many2one('hr.employee', string=" Employee")

    @api.onchange('emp_id')
    def set_hiring_date(self):
        self.date_from = self.emp_id.hiring_date

    def print_report(self):
        for report in self:
            report_name = 'Employee Social Insurance '
            report_title = 'Employee Social Insurance'
            file_name = _('insurance.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('national')
            excel_sheet.right_to_left()
            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#808080', 'border': 1})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            header_format.set_align('center')
            header_format.set_text_wrap()
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            title_format.set_align('center')
            format.set_align('center')
            header_format_sequence.set_align('center')
            format.set_text_wrap()
            format.set_num_format('#,##0.00')
            format_details = workbook.add_format()
            format_details.set_num_format('#,##0.00')
            sequence_id = 0
            col = 0
            row = 3
            excel_sheet.set_column(0, 4, 25)
            excel_sheet.set_row(1, 25)

            excel_sheet.write(row, col, 'Social Insurance 17%', header_format)
            col += 1
            excel_sheet.write(row, col, 'To Date', header_format)
            col += 1
            excel_sheet.write(row, col, 'From Date', header_format)
            col += 1
            excel_sheet.write(row, col, 'Employee Name', header_format)
            col += 1
            excel_sheet.write(row, col, 'Employee Code', header_format)
            excel_sheet.set_column(0, 4, 20)
            excel_sheet.set_row(5, 20)
            excel_sheet.merge_range(0, 0, 1, 3, report_title, title_format)
            excel_sheet.merge_range(1, 0, 2, 3, '', format)
            excel_sheet.cols_left_to_right = 1
            paysheet_details_ids = report.env['hr.payslip'].search(
                [('employee_id', '=', report.emp_id.id)])
            if paysheet_details_ids:
                for employee in paysheet_details_ids:
                    employee_name = employee.employee_id.name
                    date_start = employee.date_from
                    date_end = employee.date_to
                    code = employee.employee_id.code
                    slip_id = employee.id
                    SocialInsCompRemain = 0.0
                    slip_ids = employee.env['hr.payslip.line'].search(
                        [('slip_id', '=', slip_id), ('employee_id', '=', employee.employee_id.id)])
                    for paysheet_details_line in slip_ids:
                        category = paysheet_details_line.code
                        if category == 'SocialInsCompRemain':
                            SocialInsCompRemain = paysheet_details_line.total

                            # SocialInsCompRemain = paysheet_details_line.SocialInsCompRemain

                    col = 0
                    row += 1

                    if SocialInsCompRemain:
                        excel_sheet.write(
                            row, col, SocialInsCompRemain, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if date_start:
                        excel_sheet.write(row, col, str(date_start), format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if date_end:
                        excel_sheet.write(row, col, str(date_end), format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if employee_name:
                        excel_sheet.write(row, col, employee_name, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if code:
                        excel_sheet.write(row, col, code, format)
                    else:
                        excel_sheet.write(row, col, '', format)

            workbook.close()
            file_download = base64.b64encode(fp.getvalue())
            fp.close()
            wizardmodel = self.env['insurance.basic.list.excel']
            res_id = wizardmodel.create(
                {'name': file_name, 'file_download': file_download})
            return {
                'name': 'Files to Download',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'insurance.basic.list.excel',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': res_id.id,
            }


class InsuranceBasicListExcel(models.TransientModel):
    _name = 'insurance.basic.list.excel'
    _description = 'Insurance Basic List Excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
