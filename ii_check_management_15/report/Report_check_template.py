# -*- coding: utf-8 -*-
from odoo import api, models,fields
import datetime
from datetime import date, timedelta,datetime
import re


class wizard_Custom_Report(models.AbstractModel):
    _name = 'report.check_followups.check_bank_template1'


    @api.model
    def get_report_values(self, docids, data=None):
       report_obj = self.env['check_followups.check_followups'].search([('payment_id', '=', data['id'])])
       a=""
       b=""

       if re.match('[A-Z]',data['Name'])!=None:
            a="text-align: left;"

       else:a="text-align: right;"
       if re.match('[A-Z]', data['Amount_in_text']): #report_obj.payment_id.check_amount_in_words
           b  = "text-align: left;"
       else:
           b="text-align: right;"

       return {
           'doc': report_obj,
           'name':data['Name'],
           'Date': 'position:absolute;left: ' + str(report_obj.bank_id.datex) + ' mm;top : '+  str(report_obj.bank_id.datey) + ' mm;',
           'amount': 'position:absolute;left: ' + str(report_obj.bank_id.amountx) + ' mm;top : ' + str(report_obj.bank_id.amounty) + ' mm;',
           'amount_text': 'position:absolute;left: ' + str(report_obj.bank_id.amount_textx) + ' mm;top : ' + str(report_obj.bank_id.amount_texty) + ' mm;'"width:"+str( report_obj.bank_id.money_text_width)+"mm;"+' mm;'"height:"+str( report_obj.bank_id.money_text_height)+"mm;"+b,
           'account_holder': 'position:absolute;left: ' + str(report_obj.bank_id.acc_holderx) + ' mm;top : ' + str(report_obj.bank_id.acc_holdery) + ' mm;'+a+"width:"+str( report_obj.bank_id.account_holder_width)+"mm;",
           'Amount_in_text':data['Amount_in_text']
        }
