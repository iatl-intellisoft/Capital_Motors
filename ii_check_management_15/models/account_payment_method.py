from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['check_printing'] = {'mode': 'multi', 'domain': [('type', '=', 'bank')]}
        return res
