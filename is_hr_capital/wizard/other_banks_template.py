# -*- coding: utf-8 -*-
###########

from odoo import fields, models, _
import xlsxwriter
import base64
from datetime import datetime
from odoo.exceptions import UserError
from dateutil import relativedelta
from io import BytesIO


class WizardOtherBanks(models.TransientModel):
    _name = 'wizard.other.banks'
    _description = 'Print Salaries to Bank'

    from_date = fields.Date(string='Date From', required=True)
    to_date = fields.Date(string='Date To', required=True,
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    bank_id = fields.Many2one('res.bank', string='Bank', required=True)#hr.bank
    name = fields.Char(string="Payslip")

    # @api.multi
    def print_report(self):
        for report in self:
            from_date = report.from_date
            to_date = report.to_date
            wizard_bank_id = report.bank_id.name
            if self.from_date > self.to_date:
                raise UserError(
                    _("You must be enter start date less than end date !"))
            # report.name = ('Pay Sheet From ' + from_date + ' To ' + to_date)
            # report_title = ('Salaries From ' + from_date + ' To ' + to_date)
            report_title = ' Pay Sheet ' + \
                str(from_date) + ' to ' + str(to_date)
            file_name = _('Pay Sheet.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Pay Sheet')
            # excel_sheet.left_to_left()
            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#808080', 'border': 1})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            title = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#66b3ff', 'border': 1, 'align': 'center'})
            title_payslip = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#00ace6', 'border': 1, 'align': 'center'})
            title_header = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#66d9ff', 'border': 1, 'align': 'center'})
            title_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format.set_text_wrap()
            title_format.set_align('center')
            format.set_align('center')
            header_format_sequence.set_align('center')
            header_format.set_align('center')
            header_format.set_text_wrap()
            excel_sheet.set_row(5, 20)
            excel_sheet.set_column('F:U', 20,)
            format.set_text_wrap()
            format.set_num_format('#,##0.00')
            format_details = workbook.add_format()
            format_details.set_num_format('#,##0.00')
            sequence_id = 0
            col = 0
            row = 5
            first_row = 7
            excel_sheet.write(row, col, '#',  header_format)
            col += 1
            excel_sheet.write(row, col, 'Name', header_format)
            col += 1
            excel_sheet.write(row, col, 'Bank', header_format)
            col += 1
            excel_sheet.write(row, col, 'Type Account', header_format)
            col += 1
            excel_sheet.write(row, col, 'Account No', header_format)
            col += 1
            excel_sheet.write(row, col, 'Amount', header_format)
            col += 1
            excel_sheet.set_column(0, 3, 25)
            excel_sheet.set_row(1, 25)
            excel_sheet.merge_range(0, 0, 0, 4, report_title, title_format)
            excel_sheet.merge_range(
                2, 0, 2, 4, report.bank_id.name, title_format)
            # excel_sheet.merge_range(0, 0, 1, 10, '', title_format)

            # excel_sheet.merge_range(4, 7, 4, 13,'Salary & Allowances' , title)
            # excel_sheet.merge_range(4, 20, 4, 21,'Assignment Allowances' , title_payslip)
            # excel_sheet.merge_range(4, 22, 4, 24,'Total Salary' , title_header)
            # excel_sheet.merge_range(4, 17, 4, 19,'Deductions' , title)
            # excel_sheet.merge_range(4, 0, 4, 6,'' , title_header)
            # excel_sheet.merge_range(4, 14, 4, 16,'' , title_header)
            payslip_month_ids = report.env['hr.payslip'].search(
                [('date_to', '<=', to_date), ('date_from', '>=', from_date), ('employee_id.bank_account_id.bank_id', '=', report.bank_id.id)])
            if payslip_month_ids:
                for payslip_period in payslip_month_ids:
                    slip_id = payslip_period.id
                    employee = payslip_period.employee_id.id
                    employee_id = payslip_period.employee_id.name
                    journal = payslip_period.employee_id.contract_id.journal_id.type
                    employee_bank_id = payslip_period.employee_id.bank_id.name
                    branch_name = payslip_period.employee_id.type_account_id.name
                    account_no = payslip_period.employee_id.bank_account_no
                    col = 0
                    row += 1
                    sequence_id += 1
                    excel_sheet.write(row, col, sequence_id,
                                      header_format_sequence)
                    slip_ids = payslip_period.env['hr.payslip.line'].search([('slip_id', '=', slip_id),
                                                                             ('employee_id', '=', employee), ('code', '=', 'Total_Emp_Salary')])
                    amount = 0.0
                    for slip_line in slip_ids:
                        category = slip_line.code
                        if category == 'Total_Emp_Salary':
                            amount = slip_line.total
                            # if employee_bank_id == wizard_bank_id:
                    col += 1
                    if employee_id:
                        excel_sheet.write(row, col, employee_id, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if employee_bank_id:
                        excel_sheet.write(row, col, employee_bank_id, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if branch_name:
                        excel_sheet.write(row, col, branch_name, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if account_no:
                        excel_sheet.write(row, col, account_no, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    excel_sheet.write(row, col, amount, format)
                col = 0
                row += 1
                excel_sheet.merge_range(row, 0, row, 4, 'Total', header_format)
                excel_sheet.write_formula(row, col + 5, 'SUM(F' + str(first_row) + ':F' + str(row) + ')',
                                          format)
        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()
        wizardmodel = self.env['banks.report.excel']
        res_id = wizardmodel.create(
            {'name': file_name, 'file_download': file_download})
        return {
            'name': 'Files to Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'banks.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': res_id.id,
        }


class banks_report_excel(models.TransientModel):
    _name = 'banks.report.excel'
    _description = 'Banks Report Excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
