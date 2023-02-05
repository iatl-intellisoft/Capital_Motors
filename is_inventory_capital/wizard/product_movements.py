# -*- coding: utf-8 -*-
###########

from odoo import fields, models, api, _
import xlsxwriter
import base64
from io import BytesIO
# from odoo.exceptions import Warning as UserError


class WizardProductMovements(models.Model):
    _name = 'wizard.product.movements'
    _description = 'Print all stock movements for specific product'

    categ_id = fields.Many2one('product.category', 'Product Category')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    from_date = fields.Datetime('From Date')
    to_date = fields.Datetime('To Date')
    name = fields.Char(string="Product Movements")

    # @api.multi
    def print_report(self):
        for report in self:
            logo = report.env.user.company_id.logo
            from_date = report.from_date
            to_date = report.to_date
            product_id = report.product_id.id
            product_name = report.product_id.name
            company_id = report.env['res.company'].search(
                [('id', '=', self.env.user.company_id.id)])
            address1 = company_id.street
            address2 = company_id.street2
            country = company_id.country_id.name
            phone = company_id.phone
            website = company_id.website
            if report.from_date > report.to_date:
                raise UserError(
                    _("You must be enter start date less than end date !"))
            report_title = product_name + ' Movements From ' + \
                str(from_date) + ' to ' + str(to_date)
            file_name = _('Product Moves.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Product Moves')
            # to convert it to base64 file
            image_data = BytesIO(base64.b64decode(logo))
            # excel_sheet.insert_image('A2', 'logo.png', {'image_data': image_data})

            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#0080ff', 'border': 1})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': 'white'})
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
            format_details = workbook.add_format()
            sequence_format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            sequence_format.set_align('center')
            sequence_format.set_text_wrap()
            total_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': '#808080', 'border': 1, 'font_size': '10'})
            total_format.set_align('center')
            total_format.set_text_wrap()
            format_details.set_num_format('#,##0.00')
            sequence_id = 0
            col = 0
            row = 7
            first_row = 9
            # excel_sheet.write_merge(0, 5, 1, 5, report_title, style_header_thin_all_main1)
            excel_sheet.merge_range(0, 1, 5, 5, report_title, title_format)
            excel_sheet.set_column(col, col, 5)
            excel_sheet.write(row, col, '#', header_format)
            col += 1
            excel_sheet.set_column(col, col, 20)
            excel_sheet.write(row, col, 'Date', header_format)
            col += 1
            excel_sheet.set_column(col, col, 25)
            excel_sheet.write(row, col, 'Source', header_format)
            col += 1
            excel_sheet.set_column(col, col, 25)
            excel_sheet.write(row, col, 'Destination', header_format)
            col += 1
            excel_sheet.set_column(col, col, 10)
            excel_sheet.write(row, col, 'Qty In', header_format)
            col += 1
            excel_sheet.set_column(col, col, 15)
            excel_sheet.write(row, col, 'Qty Out', header_format)
            total = self.env['stock.move'].search([('location_id.usage', 'not in', ('internal', 'transit')),
                                                   ('location_dest_id.usage',
                                                    'in', ('internal', 'transit')),
                                                   ('date', '<', from_date),
                                                   ('product_id', '=', product_id), ('state', '=', 'done')], order='date desc')
            total_out = self.env['stock.move'].search([('location_id.usage', 'in', ('internal', 'transit')),
                                                       ('location_dest_id.usage',
                                                        'not in', ('internal', 'transit')),
                                                       ('date', '<', from_date),
                                                       ('product_id', '=', product_id), ('state', '=', 'done')], order='date desc')
            balance = sum(total.mapped('product_qty')) - \
                sum(total_out.mapped('product_qty'))
            initial_balance = balance
            move_ids = self.env['stock.move'].search(
                [('product_id', '=', product_id), ('date', '<=', to_date), ('date', '>=', from_date),
                 ('state', '=', 'done')], order='date ASC')
            if move_ids:
                for move in move_ids:
                    quantity = move.product_qty
                    date = move.date
                    Source = move.location_id.complete_name
                    location_dest = move.location_dest_id.complete_name
                    if move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage in (
                            'internal', 'transit'):
                        move_type = 'incoming'
                    elif move.location_id.usage in ('internal', 'transit') and move.location_dest_id.usage not in (
                            'internal', 'transit'):
                        move_type = 'outgoing'
                    else:
                        continue
                    col = 0
                    row += 1
                    sequence_id += 1
                    excel_sheet.write(row, col, sequence_id, sequence_format)
                    col += 1
                    if date:
                        excel_sheet.write(row, col, date, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    # write the source and destination
                    if move_type == 'incoming':
                        col += 1
                        if Source:
                            excel_sheet.write(row, col, Source, format)
                        else:
                            excel_sheet.write(row, col, '', format)
                        col += 1
                        excel_sheet.write(row, col, location_dest, format)
                    if move_type == 'outgoing':
                        col += 1
                        excel_sheet.write(row, col, Source, format)
                        col += 1
                        if location_dest:
                            excel_sheet.write(row, col, location_dest, format)
                        else:
                            excel_sheet.write(row, col, '', format)
                    # write quants
                    if move_type == 'incoming':
                        col += 1
                        if quantity:
                            excel_sheet.write(row, col, quantity, format)
                            col += 1
                            excel_sheet.write(row, col, '', format)
                        else:
                            excel_sheet.write(row, col, '', format)
                            col += 1
                            excel_sheet.write(row, col, '', format)
                    if move_type == 'outgoing':
                        col += 1
                        if quantity:
                            excel_sheet.write(row, col, '', format)
                            col += 1
                            excel_sheet.write(row, col, quantity, format)
                col = 0
                row += 1
                excel_sheet.merge_range(
                    row, col, row, col + 3, 'Total', total_format)
                excel_sheet.write_formula(
                    row, col + 4, '=SUM(e' + str(first_row) + ':e' + str(row) + ')', total_format)
                excel_sheet.write_formula(
                    row, col + 5, '=SUM(f' + str(first_row) + ':f' + str(row) + ')', total_format)
                excel_sheet.write_formula(
                    row, col + 6, 'e' + str(row + 1) + '-f' + str(row + 1), format)
                # Initial balance and current balance
                excel_sheet.write(6, 5, 'Initial Balance ', total_format)
                excel_sheet.write(6, 6, initial_balance, format)
                row += 1
                excel_sheet.write(row, 5, 'Current Balance ', total_format)
                excel_sheet.write_formula(
                    row, 6, '=SUM(g7' + '+g' + str(row) + ')', format)
                # excel_sheet.write(row + 2, col + 1, address1, format)
                # excel_sheet.write(row + 3, col + 1, address2, format)
                # excel_sheet.write(row + 4, col + 1, country, format)
                # excel_sheet.write(row + 5, col + 1, 'Office :' + phone, format)
                # excel_sheet.write(row + 6, col + 1, 'Web :' + website, format)
            workbook.close()
            file_download = base64.b64encode(fp.getvalue())
            fp.close()
            wizardmodel = self.env['product.movements.report.excel']
            res_id = wizardmodel.create(
                {'name': file_name, 'file_download': file_download})
            return {
                'name': 'Files to Download',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.movements.report.excel',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': res_id.id,
            }


class product_movements_report_excel(models.TransientModel):
    _name = 'product.movements.report.excel'
    _description = 'Product Movements Report Excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
