# Copyright 2004-2009 Tiny SPRL (<http://tiny.be>).
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# Copyright 2015-2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    stock_currency_id = fields.Many2one('res.currency', string='Stock Valuation Currency', required=True, default=lambda self:self.env.ref('base.USD'))


