# -*- coding: utf-8 -*-

from odoo import models, fields, api , _
from odoo.exceptions import AccessError, UserError, AccessDenied
from datetime import datetime


class MoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def compute_amount_fields(self, amount, src_currency, company_currency, invoice_currency=False):
        """ Method kept for compatibility reason """
        return self._compute_amount_fields(amount, src_currency, company_currency)

    @api.model
    def _compute_amount_fields(self, amount, src_currency, company_currency):
        """ Helper function to compute value for fields debit/credit/amount_currency based on an amount and the currencies given in parameter"""
        amount_currency = False
        currency_id = False
        if src_currency and src_currency != company_currency:
            amount_currency = amount
            amount = src_currency.with_context(self._context).compute(amount, company_currency)
            currency_id = src_currency.id
        debit = amount > 0 and amount or 0.0
        credit = amount < 0 and -amount or 0.0
        return debit, credit, amount_currency, currency_id
