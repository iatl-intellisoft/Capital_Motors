from odoo.exceptions import UserError
from datetime import datetime, date, timedelta
from odoo import api, fields, models, _


class Product(models.Model):
    _inherit = "product.template"

    product_alternatives_ids = fields.One2many(
        'product.alternatives', 'product_id', 'Replacement/alternative Part NO')
    average_cost = fields.Float(
        'Average cost', compute='_compute_average_cost', digits=0)
    # main_bin = fields.Many2one('bin.location', string='Form BIN')
    # to_bin = fields.Many2one('bin.location', string='To BIN')
    # redsea_bin = fields.Many2one('bin.location', string='Red Sea BIN')
    # old_bins = fields.Many2many('bin.location', string='Old Main BINs')
    product_brand = fields.Many2one(
        'brand.brand', string='Brand', required=True)
    az_margin = fields.Float(string='Margin', default=0)
    is_car = fields.Boolean(string="Is Car")
    model = fields.Many2one("model.model", "Model")
    model_year = fields.Char("Model Year")

    _sql_constraints = [
        ('default_code_uniq', 'unique(default_code)', 'The Part NO  must be unique !')
    ]
    _sql_constraints = [
        ('default_code_uniq', 'Check(1=1)', 'The Part NO  must be unique !')
    ]

    # @api.constrains('default_code','product_brand')
    # def _po_constrain(self):
    #     for rec in self :
    #         existing_product = self.env['product.template'].search(
    #             [('id', '!=', rec.id), ('default_code', '=', rec.default_code), ('product_brand', '=', rec.product_brand.id)])
    #         if existing_product:
    #             raise UserError("You can't have same  Internal Reference With Same Brand Number in Odoo twice!")

    def name_get(self):
        result = []
        for record in self:
            name = '[' + str(record.default_code) + ']' + ' ' + '[' + str(
                record.product_brand.name) + ']' + ' ' + record.name
            result.append((record.id, name))
        return result

    # @api.onchange('main_bin')
    # def onchnge_main_bin(self):
    #     for rec in self:
    #         if rec.main_bin:
    #             # mm
    #             rec.old_bins = [(4, rec.main_bin.id)]

    # @api.one
    def _compute_average_cost(self):
        total = 0.0
        length = 0
        cost_ids = self.env['product.historical.cost'].search(
            [('name', '=', self.id)])
        for line in cost_ids:
            total += line.product_price
            length += 1
        if length == 0:
            self.average_cost = total
        else:
            self.average_cost = total / length

    # @api.multi
    def _schedule_check_replacement(self):
        products = self.env['product.template'].search(
            [('qty_available', '>', 0)])
        for product in products:
            replacements = self.env['product.alternatives'].search(
                [('product_id', '=', product.id)])
            old_ref = product.default_code
            replacements_code = self.env['product.alternatives'].search(
                [('product_id', '=', product.id), ('name', '=', product.default_code)])
            if replacements_code:
                if replacements_code.alternative_qty == 0:
                    if replacements:
                        max = 0
                        for replacement in replacements:
                            if replacement.alternative_qty > max:
                                product.default_code = replacement.name
            else:
                history_vals = dict(product_id=product.id,
                                    alternative_qty=0,
                                    alternative_date=fields.datetime.now(),
                                    name=product.default_code)
                product.product_alternatives_ids.create(history_vals)
                if replacements:
                    max = 0
                    for replacement in replacements:
                        if replacement.alternative_qty > max:
                            product.default_code = replacement.name


class Brand(models.Model):
    _name = 'brand.brand'
    _description = 'Brand of the Spare'
    _order = 'name asc'

    name = fields.Char('Make', required=True)
    image_128 = fields.Image("Logo", max_width=128, max_height=128)


class Model(models.Model):
    _name = 'model.model'
    _description = 'Model of the Spare'
    _order = 'name asc'

    name = fields.Char('Model Name', required=True)


class ProductAlternatives(models.Model):
    _name = "product.alternatives"
    _description = "Product Alternatives"

    product_id = fields.Many2one('product.template', 'Alternative')
    name = fields.Char('Part Number', required=True)
    alternative_date = fields.Datetime('Date', required=True)
    alternative_qty = fields.Float('Qty')


class ProductHistoricalCost(models.Model):
    _name = "product.historical.cost"
    _description = "Product Historical Cost"

    name = fields.Many2one('product.template', 'Product')
    product_price = fields.Float('Product Cost')
    purchase_date = fields.Datetime('Purchase Date')


# Part no

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # add part no field and record historical costs  ,related='move_id.pin' ,related='move_id.to_pin'
    part_no = fields.Char('Part No.')
    # package_id = fields.Many2one('bin.location', 'Source BIN', ondelete='restrict')
    # result_package_id = fields.Many2one(
    #     'bin.location', 'Destination BIN',
    #     ondelete='restrict', required=False, )
    on_hand_qty = fields.Float(
        compute='_compute_rfq_qty', string='Quantity Remaining ')

    @api.depends('product_id')
    def _compute_rfq_qty(self):
        for rec in self:
            rec.on_hand_qty = rec.product_id.qty_available


class StockMove(models.Model):
    _inherit = 'stock.move'

    # add part no field and record historical costs
    part_no = fields.Char('Part No.')
    is_car = fields.Boolean('is car')
    # package_id = fields.Many2one('bin.location', 'Source BIN')
    # result_package_id = fields.Many2one('bin.location', 'Destination BIN')
    on_hand_qty = fields.Float(
        compute='_compute_rfq_qty', string='Quantity Remaining ')

    @api.depends('product_id')
    def _compute_rfq_qty(self):
        for rec in self:
            rec.on_hand_qty = rec.product_id.qty_available

    # @api.depends('product_id', 'location_id')
    # def _calculate_bin(self):
    #     for rec in self:
    #         source_bin = self.env['bin.location'].search([('location_id', '=', rec.location_id.id)])
    #         print("jhkjhfffffffffffffffffffffffffffffff", source_bin)
    #         for bin in source_bin:
    #             if bin.id == rec.product_id.main_bin.id:
    #                 rec.package_id = rec.product_id.main_bin.id
    #             elif bin.id == rec.product_id.redsea_bin.id:
    #                 rec.package_id = rec.product_id.redsea_bin.id
    #
    #         rec.package_id = rec.package_id
    #
    #         dest_bin = self.env['bin.location'].search([('location_id', '=', rec.location_dest_id.id)])
    #         for bin in dest_bin:
    #             if bin.id == rec.product_id.main_bin.id:
    #                 rec.result_package_id = rec.product_id.main_bin
    #             elif bin.id == rec.product_id.redsea_bin.id:
    #                 rec.result_package_id = rec.product_id.redsea_bin
    #         rec.result_package_id = rec.result_package_id

    # def _action_done(self):
    #     res = super(StockMove, self)._action_done()
    #     for move in res:
    #         if move.part_no:
    #             move._add_part_no()
    #         historical_cost = self.env['product.historical.cost']
    #         historical_cost_vals = dict(name=move.product_id.product_tmpl_id.id,
    #                                     product_price=move.price_unit,
    #                                     purchase_date=fields.Datetime.now())
    #         historical_cost.create(historical_cost_vals)

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=False)
        for move in res:
            move._add_part_no()

    def _add_part_no(self):
        if self.product_id:
            # no_of_roll = 0
            if self.picking_id.picking_type_code == 'incoming' and self.product_id.default_code:
                if not self.part_no:
                    raise UserError(_('Wrong Part No.Please Add Part No'))
                x_ids = self.env['product.alternatives'].search(
                    [('product_id', '=', self.product_id.product_tmpl_id.id)])
                if x_ids:
                    for x in x_ids:
                        rec = x_ids.search([('name', '=', self.part_no)])
                        if rec:
                            qty = self.quantity_done + x.alternative_qty
                            part_no = self.part_no

                            self.env.cr.execute(
                                """update product_alternatives set alternative_qty = %s where name= %s and id=%s ;""",
                                [qty, part_no, x.id])
                        else:
                            history_vals = dict(product_id=self.product_id.product_tmpl_id.id,
                                                alternative_qty=self.quantity_done,
                                                name=self.part_no, alternative_date=self.date, )
                            self.product_id.product_alternatives_ids.create(
                                history_vals)
                else:
                    history_vals = dict(product_id=self.product_id.product_tmpl_id.id,
                                        alternative_qty=self.quantity_done,
                                        name=self.part_no, alternative_date=self.date)
                    self.product_id.product_alternatives_ids.create(
                        history_vals)

            elif self.picking_id.picking_type_code == 'outgoing':
                x_ids = self.env['product.alternatives'].search(
                    [('product_id', '=', self.product_id.product_tmpl_id.id)])
                for x in x_ids:
                    rec = x_ids.search([('name', '=', self.part_no)])
                    if rec:
                        qty = x.alternative_qty - self.quantity_done
                        part_no = self.part_no
                        if qty < 0.0:
                            raise UserError(_(
                                "The quantity %(qty)s of  Part No %(no)s are  not available for product %(product_id)s") % {
                                'qty': -qty,
                                'product_id': self.product_id.name,
                                'no': self.part_no,
                            })
                        if not part_no and self.product_id.defualt_code:
                            raise UserError(
                                _('You need to add Part No for product %s.') % self.product_id.name)

                        self.env.cr.execute(
                            """update product_alternatives set alternative_qty = %s where  name= %s and id=%s ;""",
                            [qty, part_no, x.id])
                    else:
                        raise UserError(
                            _('Wrong Part No., Item has no part no like this'))


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def button_validate(self):
        res = super(LandedCost, self).button_validate()
        historical_cost = self.env['product.historical.cost']
        for transfer in self.picking_ids:
            for product in transfer.move_ids_without_package:
                total_landed_cost = 0.0
                for cost in self.valuation_adjustment_lines:
                    if cost.product_id.id == product.product_id.id:
                        total_landed_cost += cost.additional_landed_cost
                product_cost = historical_cost.search(
                    [('name', '=', product.product_id.product_tmpl_id.id), ('purchase_date', '=', transfer.date_done)])
                product_cost.update(
                    {'product_price': product_cost.product_price + total_landed_cost})


class StockPicking(models.Model):
    _inherit = "stock.picking"

    delay_justification = fields.Text("Delay Justification")
    # vendor_po_no = fields.Char(related='group_id.vendor_po_no')
    # p_id = fields.Many2one('purchase.order' , compute ="compute_p_id")

    # @api.depends('group_id')
    # def compute_p_id(self):
    #     for rec in self :
    #         rec.p_id = rec.group_id.p_id.id

    # def action_set_done_qty(self):
    #     for line in self.move_ids_without_package:
    #         line.update({
    #             'quantity_done': line.product_uom_qty,
    #         })
    #         line.move_line_ids.update({
    #             'package_id': line.package_id.id,
    #             'result_package_id': line.result_package_id.id
    #         })


# class QuantPackage(models.Model):
#     """ Packages containing quants and/or other packages """
#     _inherit = "bin.location"
#
#     name = fields.Char('BIN Reference')
#     bin_location_id = fields.Many2one('stock.location', 'BIN Location')
#     location_id = fields.Many2one('stock.location', 'Location', compute="_compute_package_info")
#
#     @api.depends('quant_ids.package_id', 'quant_ids.location_id', 'quant_ids.company_id', 'quant_ids.owner_id',
#                  'quant_ids.quantity', 'quant_ids.reserved_quantity')
#     def _compute_package_info(self):
#         for package in self:
#             values = {'location_id': package.bin_location_id.id, 'company_id': self.env.user.company_id.id,
#                       'owner_id': False}
#             if package.quant_ids:
#                 values['location_id'] = package.quant_ids[0].location_id
#                 if all(q.owner_id == package.quant_ids[0].owner_id for q in package.quant_ids):
#                     values['owner_id'] = package.quant_ids[0].owner_id
#                 if all(q.company_id == package.quant_ids[0].company_id for q in package.quant_ids):
#                     values['company_id'] = package.quant_ids[0].company_id
#             if package.bin_location_id:
#                 package.location_id = package.bin_location_id.id
#             package.location_id = values['location_id']
#             package.company_id = values['company_id']
#             package.owner_id = values['owner_id']


class Inventory(models.Model):
    _inherit = "stock.quant"

    # package_id = fields.Many2one(
    #     'bin.location', 'Inventoried BIN',
    #     readonly=True,
    #     states={'draft': [('readonly', False)]},
    #     help="Specify Pack to focus your inventory on a particular BIN.")

    @api.model
    def _selection_filter(self):
        """ Get the list of filter allowed according to the options checked
        in 'Settings\Warehouse'. """
        res_filter = [
            ('none', _('All products')),
            ('category', _('One product category')),
            ('product', _('One product only')),
            ('partial', _('Select products manually'))]

        if self.user_has_groups('stock.group_tracking_owner'):
            res_filter += [('owner', _('One owner only')),
                           ('product_owner', _('One product for a specific owner'))]
        if self.user_has_groups('stock.group_production_lot'):
            res_filter.append(('lot', _('One Lot/Serial Number')))
        if self.user_has_groups('stock.group_tracking_lot'):
            res_filter.append(('pack', _('A BIN')))
        return res_filter


# class InventoryLine(models.Model):
#     _inherit = "stock.inventory.line"

    # package_id = fields.Many2one(
    #     'bin.location', 'BIN', index=True)

# class Bin_loction(models.Model):
#     _name = "bin.location"
#
#     name = fields.Char("Bin Name" , required=True)
#     bin_id = fields.Many2one("stock.location")

# class StockLocation(models.Model):
#     _inherit = "stock.location"
#
#     bin_ids = fields.One2many('bin.location','bin_id', 'Bin Name')
