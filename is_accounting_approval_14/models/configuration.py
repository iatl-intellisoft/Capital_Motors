##############################################################################
#    Description: Accounting Approval                                        #
#    Author: IATL-IntelliSoft Software                                       #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################

import base64
from odoo import models, fields, api, _, tools
from odoo.tools import image_process

# Inherit to add manager for approvals
class res_users(models.Model):
    _inherit = 'res.users'

    approval_manager = fields.Many2one('res.users', 'Manager for Approval(s)')
    user_signature = fields.Binary('Signature')
    resized_user_signature = fields.Binary('Resized Signature', store=True, compute="_get_image")

    @api.depends('user_signature')
    def _get_image(self):
        if self.user_signature:
            self.resized_user_signature = self.user_signature

    def resize_signature(self):
        if self.user_signature:
            image = tools.image_fix_orientation(tools.base64_to_image(self.user_signature))
            self.resized_user_signature = image_process(self.user_signature, size=(100, 50))


# Inherit to add currency units in Arabic
class res_currency(models.Model):
    _inherit = 'res.currency'

    narration_ar_un = fields.Char('Arabic Narration Main')
    narration_ar_cn = fields.Char('Arabic Narration Denomination')
