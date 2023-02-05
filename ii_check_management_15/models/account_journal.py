# -*- coding: utf-8 -*-

from odoo import models, fields, api , _
from odoo.exceptions import AccessError, UserError, AccessDenied
from datetime import datetime


class JournalAccount(models.Model):
    _inherit = 'account.journal'

    rdc = fields.Many2one('account.account', 'Return Checks')
    rdv = fields.Many2one('account.account', 'Return Checks')
