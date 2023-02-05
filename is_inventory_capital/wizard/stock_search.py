# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Order Point Method:
#    - Order if the virtual stock of today is below the min of the defined order point
#

from odoo import api, fields, models, _


class StockSearch(models.TransientModel):
    _name = 'stock.search'
    _description = 'Stock Search'

    text = fields.Char('Enter Search Text', required=True)

    # @api.multi
    def find(self):
        tree_view_id = self.env.ref('product.product_template_tree_view').id
        form_view_id = self.env.ref(
            'product.product_template_only_form_view').id
        oe_search_result = []
        # Name Search
        product_names = self.env['product.product'].search(
            [('name', 'ilike', self.text)])
        if product_names:
            for name in product_names:
                oe_search_result.append(name.id)

        # English Desc search
        # product_en_desc = self.env['product.product'].search([('description_en', 'ilike', self.text)])
        # if product_en_desc:
        #     for desc in product_en_desc:
        #         oe_search_result.append(desc.id)

        # InternL REF search
        product_ref = self.env['product.product'].search(
            [('default_code', 'ilike', self.text)])
        if product_ref:
            for ref in product_ref:
                oe_search_result.append(ref.id)

        # # Lots search
        # product_lots = self.env['product.product'].search([('lots_ids.product_lot_name', 'ilike', self.text)])
        # if product_lots:
        #     for lot in product_lots:
        #         #product_tmpl_id = self.env['product.template'].search([('id', '=',lot.product_lot_id)])
        #         oe_search_result.append(lot.id)
        # Alternative seatch
        product_alternatives = self.env['product.product'].search(
            [('product_alternatives_ids.name', 'ilike', self.text)])
        if product_alternatives:
            for alter in product_alternatives:
                # product_tmpl_id = self.env['product.template'].search([('id', '=', alter.product_id)])
                oe_search_result.append(alter.id)

        return {
            'type': 'ir.actions.act_window',
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'view_id': tree_view_id,
            'view_mode': 'tree,form',
            'name': _('Products'),
            'res_model': 'product.product',
            'domain': [('id', 'in', oe_search_result)],
            'context': self.env.context,
            'target': 'current',
            'nodestroy': True
        }
