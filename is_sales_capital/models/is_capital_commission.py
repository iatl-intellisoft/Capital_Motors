from datetime import datetime, timedelta, date
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CRMTeam(models.Model):
    _inherit = "crm.team"

    product_category = fields.Many2one("product.category", "Product Category")
    product_category_ids = fields.Many2many("product.category")


class EmployeeComm(models.Model):
    _name = "employee.commission"
    _description = "Employee Commission"

    emp_id = fields.Many2one("hr.employee", "Employee Name")
    commission_amount = fields.Float("Commission Amount")
    debit_account = fields.Many2one("account.account", "Debit Account")
    commission_id = fields.Many2one("sale.commission")
    move_id = fields.Many2one('account.move', "Journal Ref")


class SalesCommission(models.Model):
    _name = "sale.commission"
    _description = "Sale Commission"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "sale_order_id"

    # sale_person_id = fields.Many2one("res.users", string="Salesperson")
    # sale_manger_id = fields.Many2one("res.users", string="Sales Manger")
    sale_order_id = fields.Char("Sale Order REF")
    sale_order_amount = fields.Float("Total Sale Order")
    has_journal = fields.Boolean("is Paid")
    # commission_amount = fields.Float("Commission Amount")
    date = fields.Date("Date")
    employee_comm_ids = fields.One2many(
        "employee.commission", "commission_id", "Employee Commission")
    journal_id = fields.Many2one("account.journal", "Journal")
    credit_account = fields.Many2one("account.account", "Credit Account")
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('done', 'Done'),
        ('refuse', 'Refused'),
    ], string='Status', readonly=True, tracking=True, copy=False, default='draft')

    # def button_invoices(self):
    #     views = [(self.env.ref('account.view_move_tree').id, 'tree'),
    #              (self.env.ref('account.view_move_form').id, 'form')]
    #     return {
    #         'name': _('Journal Entries'),
    #         'view_type': 'form',
    #         'view_mode': 'tree,form',
    #         'res_model': 'account.move',
    #         'view_id': False,
    #         'views': views,
    #         'type': 'ir.actions.act_window',
    #         'domain': [('id', '=', self.move_id)],
    #     }

    def create_journal(self):
        credit_account = self.journal_id.default_account_id.id
        journal_id = self.journal_id.id
        if not journal_id:
            raise UserError(('Please Add Journal'))

        date = datetime.now().date()
        for emp in self.employee_comm_ids:
            debit_account = emp.debit_account.id
            if not debit_account:
                raise UserError(('Please Add Debit Account'))

            debit_line_vals = {
                'name': 'Commission Amount for Sale Order #' + ' ' + str(emp.commission_id.sale_order_id),
                'debit': emp.commission_amount,
                'credit': 0.0,
                'account_id': debit_account,
            }
            credit_line_vals = {
                'name': 'Commission Amount for Sale Order #' + ' ' + str(emp.commission_id.sale_order_id),
                'debit': 0.0,
                'credit': emp.commission_amount,
                'account_id': credit_account,
            }
            line_ids = [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
            move_vals = {
                'date': date,
                'journal_id': journal_id,
                'line_ids': line_ids,
            }
            move = self.env['account.move'].create(move_vals)
            emp.move_id = move.id
        self.has_journal = True
        self.state = 'done'
        return move


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.constrains('sale_line_id')
    def material_line(self):
        for rec in self:
            rec.part_no = rec.sale_line_id.part_no


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('order_from')
    def _check_order_from(self):
        order_from = self.order_from
        if not order_from:
            raise UserError(('Please Select Sale Order From'))

    product_category = fields.Many2one("product.category", "Product Category")
    product_category_ids = fields.Many2many(
        "product.category", compute="compute_category_id", store=True)
    order_from = fields.Selection([
        ('admin', 'Administration'),
        ('sale_order', 'Sale Person'),
    ], string='Sale Order From', required=True)
    comm_created = fields.Boolean("is Has Commission")

    @api.depends('team_id')
    def compute_category_id(self):
        for rec in self:
            if rec.team_id:
                rec.product_category_ids = rec.team_id.product_category_ids.ids
            else:
                rec.product_category_ids = False

    # @api.onchange('team_id', 'order_line')
    # def onchange_sale_team(self):
    #     for rec in self:
    #         rec.order_line.team_id = rec.team_id.id

    def action_confirm(self):
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm locked or cancelled SO's
        """
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                "It is not allowed to confirm an order in the following states: %s",
                ", ".join(self._get_forbidden_state_confirm()),
            ))

        self.order_line._validate_analytic_distribution()

        for order in self:
            if order.partner_id in order.message_partner_ids:
                continue
            order.message_subscribe([order.partner_id.id])

        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        self.comm_form()
        return True

    @api.onchange('order_from', 'order_line')
    def calculate_comm(self):
        for rec in self:
            if rec.order_from == "admin":
                total_comm = 0.01 * rec.amount_total
                rec.order_line.sale_person_comm = 0.7 * total_comm
                rec.order_line.sale_man_comm = 0.3 * total_comm

            if rec.order_from == "sale_order":
                total_comm = 0.005 * rec.amount_total
                rec.order_line.sale_person_comm = 0.7 * total_comm
                rec.order_line.sale_man_comm = 0.3 * total_comm

    def comm_form(self):
        sale_employee_id = self.env['hr.employee'].search(
            [('user_id', '=', self.user_id.id)])
        total_manger_amount = 0
        total_sale_person_amount = 0
        for line_id in self.order_line:
            total_manger_amount += line_id.sale_man_comm
            total_sale_person_amount += line_id.sale_person_comm

        sal_manger_comm = {
            'emp_id': sale_employee_id.parent_id.id,
            'commission_amount': total_manger_amount,

        }
        sale_person_com = {
            'emp_id': sale_employee_id.id,
            'commission_amount': total_sale_person_amount,

        }
        line_ids = [(0, 0, sal_manger_comm), (0, 0, sale_person_com)]
        move_vals = {
            'date': datetime.now().date(),
            'sale_order_id': self.name,
            'sale_order_amount': self.amount_total,
            'employee_comm_ids': line_ids,
        }
        commission = self.env['sale.commission'].create(move_vals)
        self.comm_created = True
        # return commission


class SaleOrderLineComm(models.Model):
    _inherit = 'sale.order.line'

    # @api.onchange('product_id')
    # def product_id_change(self):
    #     if not self.product_id:
    #         return
    #     valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
    #     # remove the is_custom values that don't belong to this template
    #     for pacv in self.product_custom_attribute_value_ids:
    #         if pacv.custom_product_template_attribute_value_id not in valid_values:
    #             self.product_custom_attribute_value_ids -= pacv

    #     # remove the no_variant attributes that don't belong to this template
    #     for ptav in self.product_no_variant_attribute_value_ids:
    #         if ptav._origin not in valid_values:
    #             self.product_no_variant_attribute_value_ids -= ptav

    #     vals = {}
    #     if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
    #         vals['product_uom'] = self.product_id.uom_id
    #         vals['product_uom_qty'] = self.product_uom_qty or 1.0

    #     product = self.product_id.with_context(
    #         lang=self.order_id.partner_id.lang,
    #         partner=self.order_id.partner_id,
    #         quantity=vals.get('product_uom_qty') or self.product_uom_qty,
    #         date=self.order_id.date_order,
    #         pricelist=self.order_id.pricelist_id.id,
    #         uom=self.product_uom.id
    #     )

    #     vals.update(
    #         name=self.get_sale_order_line_multiline_description_sale(product))

    #     self._compute_tax_id()
    #     self.purchase_price = self.product_id.standard_price
    #     self.part_no = self.product_id.default_code

    #     if self.order_id.pricelist_id and self.order_id.partner_id:
    #         vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
    #             self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
    #     self.update(vals)

    #     title = False
    #     message = False
    #     result = {}
    #     warning = {}
    #     if product.sale_line_warn != 'no-message':
    #         title = _("Warning for %s") % product.name
    #         message = product.sale_line_warn_msg
    #         warning['title'] = title
    #         warning['message'] = message
    #         result = {'warning': warning}
    #         if product.sale_line_warn == 'block':
    #             self.product_id = False

    #     return result

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            line.purchase_price = line.product_id.standard_price
            line.part_no = line.product_id.default_code
            product = line.product_id.with_context(
                lang=line.order_id.partner_id.lang,
                partner=line.order_id.partner_id,
                quantity=line.product_uom_qty,
                date=line.order_id.date_order,
                pricelist=line.order_id.pricelist_id.id,
                uom=line.product_uom.id
            )
            if line.qty_invoiced > 0:
                continue
            if not line.product_uom or not line.product_id or not line.order_id.pricelist_id:
                line.price_unit = 0.0
            else:
                line.price_unit = self.env['account.tax']._fix_tax_included_price_company(
                self._get_display_price(), product.taxes_id, self.tax_id, self.company_id)

    # @api.model
    # def _get_default_team(self):
    #     return self.env['crm.team']._get_default_team_id()

    sale_man_comm = fields.Float("Manger Commission")
    sale_person_comm = fields.Float("Sale Person Commission")
    part_no = fields.Char('Part No.')
    # product_category = fields.Many2many("product.category", "sale_team_rel", "team_id", "category_id",
    #                                     related='team_id.product_category')
    # team_id = fields.Many2one('crm.team')
    # team_id = fields.Many2one(
    #     'crm.team', 'Sales Team',
    #     change_default=True, default=_get_default_team, check_company=True,  # Unrequired company
    #     domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

#
# class ProductProduct(models.Model):
#     _inherit = "product.product"
#
#     @api.onchange('sale_price_usd', 'profit')
#     def onchange_sale_price_usd(self):
#         currency_rate = self.env['res.currency.rate'].search(
#             [('currency_id.name', '=', 'USD'), ('name', '=', fields.Date.today())], limit=1).rate
#         if not currency_rate:
#             currency_rate = self.env['res.currency.rate'].search(
#                 [('currency_id.name', '=', 'USD'), ('name', '<', fields.Date.today())], limit=1).rate
#         if currency_rate:
#             self.lst_price = self.sale_price_usd / currency_rate
