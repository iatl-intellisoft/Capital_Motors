# -*- coding: utf-8 -*-
###########

from odoo import fields, models, _
import xlsxwriter
import base64
from io import BytesIO
from datetime import datetime
from odoo.exceptions import UserError
from dateutil import relativedelta


class WizardPayslip(models.Model):
    _name = 'wizard.paysheet'
    _description = 'Print Payslip'

    # payslip_report = fields.Binary(string='s')
    # payslip_report_name = fields.Char(string='Payslip Name', default='Pay sheet Report.xls')
    from_date = fields.Date(string='Date From', required=True)
    # default=time.strftime('%Y-%m-01'))
    to_date = fields.Date(string='Date To', required=True,
                          default=str(
                              datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                          )
    name = fields.Char(string="Payslip")

    def print_report(self):
        for report in self:
            from_date = report.from_date
            to_date = report.to_date
            if self.from_date > self.to_date:
                raise UserError(
                    _("You must be enter start date less than end date !"))
            report.name = 'Pay Sheet From ' + \
                str(from_date) + ' To ' + str(to_date)
            report_title = 'Salaries From ' + \
                str(from_date) + ' To ' + str(to_date)
            file_name = _('Pay Sheet.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Pay Sheet')
            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#808080', 'border': 1})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            title_format.set_align('center')
            format.set_align('center')
            header_format_sequence.set_align('center')
            header_format.set_align('center')
            header_format.set_text_wrap()
            excel_sheet.set_row(5, 20)
            excel_sheet.set_column('F:U', 20, )
            format.set_text_wrap()
            format.set_num_format('#,##0.00')
            format_details = workbook.add_format()
            format_details.set_num_format('#,##0.00')
            sequence_id = 0
            col = 0
            row = 5
            first_row = 7
            excel_sheet.write(row, col, '#', header_format)
            col += 1
            excel_sheet.write(row, col, 'رقم الموظف', header_format)
            col += 1
            excel_sheet.write(row, col, 'Name', header_format)
            col += 1
            excel_sheet.write(row, col, 'Department', header_format)
            col += 1
            excel_sheet.write(row, col, 'Job  Title ', header_format)
            col += 1
            excel_sheet.write(row, col, 'Basic 48% ', header_format)
            col += 1
            excel_sheet.write(row, col, 'COLA 20%', header_format)
            col += 1
            excel_sheet.write(row, col, 'TransportationAll 18%', header_format)
            col += 1
            excel_sheet.write(row, col, 'Housing 14%', header_format)
            col += 1
            excel_sheet.write(row, col, 'Grant', header_format)
            col += 1
            excel_sheet.write(row, col, 'GROSS', header_format)
            col += 1
            excel_sheet.write(row, col, 'Tax', header_format)
            col += 1
            excel_sheet.write(row, col, 'Social Ins.', header_format)
            col += 1
            # excel_sheet.write(row, col, 'Social Ins.', header_format)
            # col += 1
            # excel_sheet.write(row, col, 'Social Ins.', header_format)
            # col += 1
            # excel_sheet.write(row, col, 'Social Ins.', header_format)
            # col += 1
            excel_sheet.write(row, col, 'Short Loan', header_format)
            col += 1
            excel_sheet.write(row, col, 'Long Loan', header_format)
            col += 1
            excel_sheet.write(row, col, 'Penalty', header_format)
            col += 1
            excel_sheet.write(row, col, 'Phone Deduction', header_format)
            col += 1
            excel_sheet.write(row, col, 'Net Salary', header_format)
            col += 1

            excel_sheet.set_column(0, 4, 25)
            excel_sheet.set_row(1, 25)
            excel_sheet.merge_range(0, 0, 1, 20, 'Capial Motors', title_format)
            excel_sheet.merge_range(2, 0, 3, 20, report_title, title_format)
            excel_sheet.merge_range(3, 0, 4, 20, '', title_format)
            payslip_month_ids = report.env['hr.payslip'].search(
                [('date_to', '<=', to_date), ('date_from', '>=', from_date), ('state', '=', 'done')])
            for payslip_period in payslip_month_ids:
                slip_id = payslip_period.id
                employee = payslip_period.employee_id.id
                employee_id = payslip_period.employee_id.name
                department_id = payslip_period.employee_id.department_id.name
                job_id = payslip_period.employee_id.job_id.name
                employee_code = payslip_period.employee_id.code
                col = 0
                row += 1
                sequence_id += 1
                excel_sheet.write(row, col, sequence_id,
                                  header_format_sequence)
                col += 1
                if employee_code:
                    excel_sheet.write(row, col, employee_code, format)
                else:
                    excel_sheet.write(row, col, '', format)
                col += 1
                if employee_id:
                    excel_sheet.write(row, col, employee_id, format)
                else:
                    excel_sheet.write(row, col, '', format)
                col += 1
                if department_id:
                    excel_sheet.write(row, col, department_id, format)
                else:
                    excel_sheet.write(row, col, '', format)
                col += 1
                if job_id:
                    excel_sheet.write(row, col, job_id, format)
                else:
                    excel_sheet.write(row, col, '', format)
                slip_ids = payslip_period.env['hr.payslip.line'].search([('slip_id', '=', slip_id),
                                                                         ('employee_id', '=', employee)])
                basic = 0.0
                cola = 0.0
                TransportationAll = 0.0
                housing = 0.
                GRANT = 0.0
                TAX = 0.0
                GROSS = 0.0
                SocialInsComp = 0.0
                SocialInsCompRemain = 0.0
                SocialIns = 0.0
                ADLOAN = 0.0
                ELOAN = 0.0
                PhoneDeduction = 0.0
                NET = 0.0
                sh_loan = 0.0

                PEN = 0.0
                attendance = 0.0
                acting_alw = 0.0
                other_deduction = 0.0
                exemption = 0.0
                for slip_line in slip_ids:
                    category = slip_line.code

                    if category == 'BASIC':
                        basic = slip_line.total
                    if category == 'COLA':
                        cola = slip_line.total
                    if category == 'TransportationAll':
                        TransportationAll = slip_line.total
                    if category == 'HousingAll':
                        housing = slip_line.total
                    if category == 'GRANT':
                        GRANT = slip_line.total
                    if category == 'GROSS':
                        GROSS = slip_line.total

                    if category == 'TAX':
                        TAX = slip_line.total
                    if category == 'SocialIns':
                        SocialIns = slip_line.amount
                    if category == 'SocialInsComp':
                        SocialInsComp = slip_line.total
                    if category == 'SocialInsCompRemain':
                        SocialInsCompRemain = slip_line.total
                    if category == 'SocialInsComp':
                        SocialInsComp = slip_line

                    if category == 'ADLOAN':
                        ADLOAN = slip_line.amount
                    if category == 'ELOAN':
                        ELOAN = slip_line.total
                    if category == 'PEN':
                        PEN = slip_line.total
                    if category == 'PhoneDeduction':
                        PhoneDeduction = slip_line.total
                    if category == 'NET':
                        NET = slip_line.amount
                    col = 5

                    # if basic:
                    excel_sheet.write(row, col, basic, format)
                    col += 1
                    excel_sheet.write(row, col, cola, format)
                    col += 1
                    excel_sheet.write(row, col, TransportationAll, format)
                    col += 1
                    excel_sheet.write(row, col, housing, format)
                    col += 1
                    excel_sheet.write(row, col, GRANT, format)
                    col += 1
                    excel_sheet.write(row, col, GROSS, format)
                    col += 1
                    excel_sheet.write(row, col, TAX, format)
                    col += 1
                    excel_sheet.write(row, col, SocialIns, format)
                    col += 1
                    excel_sheet.write(row, col, ADLOAN, format)
                    col += 1
                    excel_sheet.write(row, col, ELOAN, format)
                    col += 1
                    excel_sheet.write(row, col, PEN, format)
                    col += 1
                    excel_sheet.write(row, col, PhoneDeduction, format)
                    col += 1
                    excel_sheet.write(row, col, NET, format)
                    col += 1

        col = 0
        row += 1
        excel_sheet.merge_range(row, col, row, col + 18,
                                'Total', header_format)
        excel_sheet.write_formula(
            row, col + 19, 'SUM(t' + str(first_row) + ':t' + str(row) + ')', header_format)
        excel_sheet.write_formula(
            row, col + 20, 'SUM(u' + str(first_row) + ':u' + str(row) + ')', header_format)
        excel_sheet.write(row, col + 21, '', header_format)
        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()
        wizardmodel = self.env['payslip.report.excel']
        res_id = wizardmodel.create(
            {'name': file_name, 'file_download': file_download})
        return {
            'name': 'Files to Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payslip.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': res_id.id,
        }

    ############################################


class payslip_report_excel(models.TransientModel):
    _name = 'payslip.report.excel'
    _description = 'Payslip Report Excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
