# -*- coding: utf-8 -*-
###########

from odoo import fields, models, _
import xlsxwriter
import base64
from io import BytesIO
from datetime import datetime
from odoo.exceptions import UserError
from dateutil import relativedelta

# import sys
# reload()
# sys.setdefaultencoding('utf8')


class WizardOvertimeTest(models.Model):
    _name = 'wizard.overtime'
    _description = 'Print overtime'

    from_date = fields.Date(string='Date From', required=True)
    # , default = time.strftime('%Y-%m-01')
    to_date = fields.Date(string='Date To', required=True,
                          default=str(
                              datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                          )
    name = fields.Char(string="Overtime")

    def print_report(self):
        for report in self:
            overtime_ids = False
            from_date = report.from_date
            to_date = report.to_date
            if self.from_date > self.to_date:
                raise UserError(
                    _("You must be enter start date less than end date !"))
            report.name = 'Overtime From ' + \
                str(from_date) + ' To ' + str(to_date)
            report_title = 'Staff  Overtime' + \
                str(from_date) + ' To ' + str(to_date)
            file_name = _('Overtime.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Month Overtime')
            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'border': 1})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            contain_format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            header_date = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            footer2_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'border': 0})
            footer_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'border': 0})
            header_format.set_align('center')
            header_format.set_text_wrap()
            # format = workbook.add_format({'bold': False, 'font_color': 'black','bg_color': 'white'})
            title_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            title_format.set_align('center')
            contain_format.set_align('center')
            header_date.set_align('left')
            header_format_sequence.set_align('center')
            contain_format.set_text_wrap()
            contain_format.set_num_format('#,##0.00')
            format_details = workbook.add_format()
            format_details.set_num_format('#,##0.00')
            sequence_id = 0
            col = 0
            row = 5
            first_row = 7
            excel_sheet.set_row(1, 25)
            excel_sheet.set_column(col, col, 15)
            excel_sheet.merge_range(row, col, row+1, col, 'No', header_format)
            col += 1
            excel_sheet.set_column(col, col, 30)
            excel_sheet.merge_range(
                row, col, row+1, col, 'Name', header_format)
            col += 1
            excel_sheet.merge_range(
                row, col, row+1, col, 'Designation', header_format)
            col += 1
            excel_sheet.write(row, col, 'Basic', header_format)
            excel_sheet.write(row+1, col, 'Salary', header_format)
            col += 1
            excel_sheet.merge_range(
                row, col, row+1, col, 'Hour Value', header_format)
            col += 1
            excel_sheet.merge_range(
                row, col, row, col+1, 'Total Hours', header_format)
            excel_sheet.write(row+1, col, 'Nor', header_format)
            col += 1
            excel_sheet.write(row+1, col, '×1.5', header_format)
            col += 1
            excel_sheet.merge_range(
                row, col, row, col + 1, 'Total Hours', header_format)
            excel_sheet.write(row+1, col, 'Holi.', header_format)
            col += 1
            excel_sheet.write(row+1, col, '×2', header_format)
            col += 1
            excel_sheet.write(row, col, 'Hours', header_format)
            excel_sheet.write(row+1, col, 'Total', header_format)
            col += 1
            excel_sheet.write(row, col, 'Hours', header_format)
            excel_sheet.write(row+1, col, 'Amount', header_format)
            col += 1
            excel_sheet.merge_range(row, col, row+1, col, 'Sig', header_format)
            excel_sheet.set_column(0, 4, 20)
            excel_sheet.set_row(5, 20)
            excel_sheet.merge_range(
                0, 0, 1, 11, 'MTWA International Investment Co.LTD', title_format)
            excel_sheet.merge_range(2, 0, 3, 11, report_title, title_format)
            excel_sheet.merge_range(4, 0, 4, 11, str(
                report.create_date), header_date)
            excel_sheet.cols_left_to_right = 1
            overtime_month_ids = report.env['hr.overtime.month'].search(
                [('date_to', '<=', to_date), ('date_from', '>=', from_date)])
            for overtime_month in overtime_month_ids:
                overtime_month_id = overtime_month.id
                overtime_ids = report.env['overtime.line'].search(
                    [('overtime_line_id', '=', overtime_month_id)])
            if overtime_ids:
                employee_id = False
                overtime_month = 0.0
                overtime_month_value = 0.0
                for overtime_line in overtime_ids:
                    col = 0
                    row += 1
                    sequence_id += 1
                    employee_id = overtime_line.name.name
                    job = overtime_line.name.job_id.name
                    employee_hour_salary = overtime_line.employee_hour_salary
                    employee_salary = overtime_line.employee_salary
                    overtime_month = overtime_line.overtime_month
                    overtime_month_value = overtime_line.overtime_month_value
                    total_work_hour = overtime_line.total_work_hour
                    total_work_overtime = overtime_line.total_work_overtime
                    total_holiday_hour = overtime_line.total_holiday_hour
                    total_holiday_overtime = overtime_line.total_holiday_overtime

                    excel_sheet.write(row+1, col, sequence_id,
                                      header_format_sequence)
                    col += 1
                    if employee_id:
                        excel_sheet.write(
                            row+1, col, employee_id, contain_format)
                    else:
                        excel_sheet.write(row+1, col, '', contain_format)
                    col += 1
                    if job:
                        excel_sheet.write(row+1, col, job, contain_format)
                    else:
                        excel_sheet.write(row+1, col, '', contain_format)
                    col += 1
                    if employee_salary:
                        excel_sheet.write(
                            row+1, col, employee_salary, contain_format)
                    else:
                        excel_sheet.write(row+1, col, '', contain_format)
                    col += 1
                    if employee_hour_salary:
                        excel_sheet.write(
                            row+1, col, employee_hour_salary, contain_format)
                    else:
                        excel_sheet.write(row+1, col, '', contain_format)
                    col += 1
                    if total_work_hour:
                        excel_sheet.write(
                            row+1, col, total_work_hour, contain_format)
                    else:
                        excel_sheet.write(row+1, col, 0.0, contain_format)
                    col += 1
                    if total_work_overtime:
                        excel_sheet.write(
                            row+1, col, total_work_overtime, contain_format)
                    else:
                        excel_sheet.write(row+1, col, 0.0, contain_format)
                    col += 1
                    if total_holiday_hour:
                        excel_sheet.write(
                            row+1, col, total_holiday_hour, contain_format)
                    else:
                        excel_sheet.write(row+1, col, 0.0, contain_format)
                    col += 1
                    if total_holiday_overtime:
                        excel_sheet.write(
                            row+1, col, total_holiday_overtime, contain_format)
                    else:
                        excel_sheet.write(row+1, col, 0.0, contain_format)
                    col += 1
                    if overtime_month:
                        excel_sheet.write(
                            row+1, col, overtime_month, contain_format)
                    else:
                        excel_sheet.write(row+1, col, '', contain_format)
                    col += 1
                    if overtime_month_value:
                        excel_sheet.write(
                            row+1, col, overtime_month_value, contain_format)
                    else:
                        excel_sheet.write(row+1, col, '', contain_format)
                    col += 1
                    excel_sheet.write(row + 1, col, '', contain_format)
            col = 0
            row += 1
            col_8 = '8'
            excel_sheet.merge_range(
                row+1, col, row+1, col + 9, 'Total', header_format)
            # excel_sheet.write_formula(row+1, col + 10, 'SUM(k' + col_8.encode('utf8') + ':k' + str(row) + ')', contain_format)
            excel_sheet.write_formula(
                row+1, col + 10, 'SUM(k' + col_8 + ':k' + str(row) + ')', contain_format)
            excel_sheet.write(row + 1, col+11, 'SDG', contain_format)
            footer_format.set_underline()
            excel_sheet.write(row + 2, col + 1, 'Prepared by:', footer_format)
            excel_sheet.write(row + 3, col + 1,
                              report.create_uid.name, footer2_format)
            excel_sheet.write(row + 4, col + 1,
                              'HR & Admin Manager', footer2_format)
            excel_sheet.write(row + 2, col + 6,
                              ' Approved by: ', footer_format)
            excel_sheet.write(row + 4, col + 6,
                              'Finance & Accounting Manager', footer2_format)
            workbook.close()
            file_download = base64.b64encode(fp.getvalue())
            fp.close()
            wizardmodel = self.env['overtime.month.excel']
            res_id = wizardmodel.create(
                {'name': file_name, 'file_download': file_download})
            return {
                'name': 'Files to Download',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'overtime.month.excel',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': res_id.id,
            }


############################################
class overtime_report_excel(models.TransientModel):
    _name = 'overtime.month.excel'
    _description = 'Overtime Month Excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
