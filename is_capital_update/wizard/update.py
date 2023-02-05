# -*- coding: utf-8 -*-
from odoo import api, models, fields


class update_contract(models.TransientModel):
    _name = "update.contract"
    _description = "Update Contract"

    def update_contract(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        for rec in self.env['hr.contract'].browse(active_ids):
            rec.official_sal_per = rec.wage/2
