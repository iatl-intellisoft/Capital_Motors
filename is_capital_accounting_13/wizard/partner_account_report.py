# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import xlsxwriter
import base64
from io import BytesIO
from datetime import datetime


class AccountCustomReport(models.Model):
    _name = 'account.custom.report'
    _description = 'Print Account Report'

    account = fields.Many2one('account.account', string='Account',
                              domain="[('account_type', 'in', ('asset_receivable', 'liability_payable'))]")
    partner = fields.Many2one('res.partner', string='Partner')
    name = fields.Char(string="Account Report")

    def print_report(self):
        for report in self:
            account = report.account.id
            partner = report.partner.id
            # report.name = 'Account Partner Report '
            report_title = 'Account Partner Report'
            file_name = _('Account Partner.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('')
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
            # excel_sheet.set_row(5, 0)
            # excel_sheet.set_column('F:U', 20, )
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
            excel_sheet.write(row, col, 'Account', header_format)
            col += 1
            excel_sheet.write(row, col, 'Partner', header_format)
            col += 1
            excel_sheet.write(row, col, 'Debit', header_format)
            col += 1
            excel_sheet.write(row, col, 'Credit', header_format)
            col += 1
            excel_sheet.set_column(0, 4, 25)
            excel_sheet.set_row(1, 25)
            # excel_sheet.merge_range(0, 0, 1, 5, 'Account Partner', title_format)
            excel_sheet.merge_range(2, 0, 3, 5, report_title, title_format)
            excel_sheet.merge_range(3, 0, 4, 20, '', title_format)
            account_move_lines = report.env['account.move.line'].search(
                [('partner_id', '=', partner), ('account_id', '=', account)])
            debit = 0
            credit = 0
            for account_move_line in account_move_lines:
                col = 0
                row += 1
                sequence_id += 1
                excel_sheet.write(row, col, sequence_id,
                                  header_format_sequence)
                col += 1
                account = report.account
                partner = report.partner

                if account:
                    excel_sheet.write(row, col, str(account.name), format)
                else:
                    excel_sheet.write(row, col, '', format)
                col += 1
                if partner:
                    excel_sheet.write(row, col, str(partner.name), format)
                col += 1
                excel_sheet.write(row, col, str(
                    account_move_line.debit), format)
                col += 1
                excel_sheet.write(row, col, str(
                    account_move_line.credit), format)

        col = 0
        row += 1
        # excel_sheet.merge_range(row, col, row, col + 18, 'Total', header_format)
        # excel_sheet.write_formula(row, col + 19, 'SUM(t' + str(first_row) + ':t' + str(row) + ')', header_format)
        # excel_sheet.write_formula(row, col + 20, 'SUM(u' + str(first_row) + ':u' + str(row) + ')', header_format)
        excel_sheet.write(row, col + 21, '', header_format)
        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()
        wizardmodel = self.env['account.report.excel']
        res_id = wizardmodel.create(
            {'name': file_name, 'file_download': file_download})
        return {
            'name': 'Files to Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': res_id.id,
        }


class account_report_excel(models.TransientModel):
    _name = 'account.report.excel'
    _description = 'Account Report Excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
