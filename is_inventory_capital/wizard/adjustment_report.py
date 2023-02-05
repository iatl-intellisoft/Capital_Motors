# -*- coding: utf-8 -*-
###########

from odoo import fields, models, api, _
import xlsxwriter
import base64
from io import BytesIO
from odoo.exceptions import UserError


class AdjustmentReport(models.Model):
    _name = 'adjustment.report'
    _description = 'Print all Products and Quantities for product Category'

    categ_id = fields.Many2one('product.category', 'Product Category')
    from_date = fields.Datetime('From Date')
    to_date = fields.Datetime('To Date')

    # @api.multi
    def print_report(self):
        for report in self:
            logo = report.env.user.company_id.logo
            from_date = report.from_date
            to_date = report.to_date
            company_id = report.env['res.company'].search(
                [('id', '=', self.env.user.company_id.id)])
            if report.from_date > report.to_date:
                raise UserError(
                    _("You must be enter start date less than end date !"))
            file_name = _('Inventory Adjustment.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Inventory Adjustment')
            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#0080ff', 'border': 1})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            header_format.set_align('center')
            header_format.set_align('vertical center')
            header_format.set_text_wrap()
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1, 'font_size': '10'})
            title_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format.set_align('center')
            format.set_align('center')
            header_format_sequence.set_align('center')
            format.set_text_wrap()
            format.set_num_format('#,##0.000')
            sequence_format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            sequence_format.set_align('center')
            sequence_format.set_text_wrap()
            total_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': '#808080', 'border': 1, 'font_size': '10'})
            col = 0
            row = 0
            excel_sheet.set_column(col, col, 25)
            excel_sheet.write(row, col, 'Product', header_format)
            col += 1
            excel_sheet.set_column(col, col, 20)
            excel_sheet.write(row, col, 'Location', header_format)
            col += 1
            excel_sheet.set_column(col, col, 20)
            excel_sheet.write(row, col, 'Lot/Serial Number', header_format)
            col += 1
            excel_sheet.set_column(col, col, 20)
            excel_sheet.write(row, col, 'Theoretical Quantity', header_format)
            col += 1
            excel_sheet.set_column(col, col, 20)
            excel_sheet.write(row, col, 'Real Quantity', header_format)
            products = self.env['product.product'].search(
                [('categ_id', '=', report.categ_id.id)])
            col = 0
            row += 1
            for product in products:
                quant_ids = self.env['stock.quant'].search(
                    [('product_id', '=', product.id)])
                for quant in quant_ids:
                    if quant.location_id.usage == 'internal':
                        excel_sheet.write(
                            row, col, quant.product_id.name, format)
                        col += 1
                        excel_sheet.write(
                            row, col, quant.location_id.display_name, format)
                        col += 1
                        excel_sheet.write(row, col, quant.lot_id.name, format)
                        col += 1
                        excel_sheet.write(row, col, quant.quantity, format)
                        col += 1
                        excel_sheet.write(row, col, ' ', format)
                        col = 0
                        row += 1
            workbook.close()
            file_download = base64.b64encode(fp.getvalue())
            fp.close()
            wizardmodel = self.env['adjustment.report.report.excel']
            res_id = wizardmodel.create(
                {'name': file_name, 'file_download': file_download})
            return {
                'name': 'Files to Download',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'adjustment.report.report.excel',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': res_id.id,
            }


class adjustment_report_excel(models.TransientModel):
    _name = 'adjustment.report.report.excel'
    _description = 'Adjustment Report Excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
