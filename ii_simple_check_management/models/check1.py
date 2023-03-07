from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging


_logger = logging.getLogger(__name__)


class CheckFollowups(models.Model):
    _name = 'check_followups.check_followups'
    _description = 'Checks Followup'
    _order = 'id desc'

    @api.depends('payment_id')
    def _compute_partners(self):
        for r in self:
            if r.payment_id:
                if r.payment_id and r.payment_id.payment_type == 'inbound':
                    r.beneficiary_id = r.payment_id.company_id.partner_id or False
                    r.account_holder = r.payment_id.partner_id or False
                elif r.payment_id and r.payment_id.payment_type == 'outbound':
                    r.beneficiary_id = r.payment_id.partner_id or False
                    r.account_holder = r.payment_id.company_id.partner_id or False
                elif r.payment_id and r.payment_id.payment_type == 'transfer':
                    r.beneficiary_id = r.account_holder = r.payment_id.company_id.partner_id or False

    name = fields.Char("Check", readonly=True, default='New')
    payment_id = fields.Many2one('account.payment')
    # payment_line_id = fields.Many2one('account.payment.check.line')
    type = fields.Selection([('outbound', 'Vendor'), ('inbound', 'Customer'), ('transfer', 'Transfer')], string="Type")
    Date = fields.Date('Date')
    amount = fields.Monetary('Amount', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    communication = fields.Char('Ref')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company'])
    check_no = fields.Char('Check No', required=True)
    account_holder = fields.Many2one('res.partner', string='Account Holder', readonly=True, compute=_compute_partners)
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary', readonly=True, compute=_compute_partners)
    partner_id = fields.Many2one('res.partner', compute='_compute_partner', readonly=True)
    bank_id = fields.Many2one('res.bank', readonly=True)
    partner_bank = fields.Char('Partner Bank')
    state = fields.Selection([
        ('under_collection', 'Under Collection'),
        ('in_bank', 'In Bank'),
        ('rdc', 'Check Rejected'),
        ('return_acc', 'Return to Partner'),
        ('donec', 'Done'),
        ('out_standing', 'Out Standing'),
        ('withdrawal', 'Withdraw From Bank'),
        ('rdv', 'Check Rejected'),
        ('return_acv', 'Return to Partner'),
        ('donev', 'Done'),
        ('cancel', 'Canceled')])
    Last_state = fields.Char()
    log_ids = fields.One2many('check_followups.checklogs', 'Check', readonly=True)

    # check_account_journal_id = fields.Many2one('account.journal', 'From Journal')
    to_account_journal_id = fields.Many2one('account.journal', 'To Journal', domain="[('type', '=', 'bank')]")

    @api.depends('payment_id')
    def _compute_partner(self):
        for r in self:
            r.partner_id = r.payment_id and r.payment_id.partner_id or False

    @api.depends('payment_id')
    def _compute_currency_id(self):
        for r in self:
            r.currency_id = r.payment_id and r.payment_id.currency_id or False

    def action_withdrawl(self):
        self.Last_state = self.state
        self.write({'state': 'withdrawal'})
        if self.payment_id and self.payment_id.check_type == 'indirect':
            self.make_move()
        return True

    @api.model
    def cron_checks_withdrawal(self):
        records = self.env['check_followups.check_followups']\
            .search([('state', 'in', ['under_collection', 'out_standing']), ('Date', '<=', fields.Date.today()),
                     ('payment_id.company_id.automate_check_withdrawal', '=', True)])
        for rec in records.filtered(lambda r: r.state == 'out_standing'):
            rec.action_withdrawl()
        for rec in records.filtered(lambda r: r.state == 'under_collection'):
            rec.action_submitted()

    def action_rejectv(self):
        self.Last_state = self.state
        self.write({'state': 'rdv'})
        self.make_move()
        return True

    def action_returnv(self):
        payment_id = self.payment_id
        for line in payment_id.line_ids:
            for rec in line.matched_credit_ids:
                payment_id.move_id.js_remove_outstanding_partial(rec.id)    
        self.Last_state = self.state
        self.write({'state': 'return_acv'})
        self.make_move()
        return True

    def action_donev(self):
        self.Last_state = self.state
        self.write({'state': 'donev'})
        return True

    def action_change_bank(self):
        return {
            'name': _('Check_Wizard'),
            # 'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'check.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_submitted(self):
        self.Last_state = self.state
        self.write({'state': 'in_bank'})
        
        if self.payment_id and self.payment_id.check_type == 'indirect':
            self.make_move()
        return True

    def action_rejectc(self):
        self.Last_state = self.state
        self.write({'state': 'rdc'})
        self.make_move()
        return True

    def action_donec(self):
        self.Last_state = self.state
        self.write({'state': 'donec'})
        return True

    def action_returnc(self, communication=''):
        payment_id = self.payment_id
        for line in payment_id.line_ids:
            for rec in line.matched_debit_ids:
                payment_id.move_id.js_remove_outstanding_partial(rec.id)

        self.Last_state = self.state
        self.write({'state': 'return_acc'})
        self.make_move()
        return True
    def make_move(self):
        for r in self:
            today_date = fields.Date.today()
            aml = r.env['account.move.line']
            debit, credit, ss, amount_currency = aml.with_context(date=r.payment_id.date).compute_amount_fields(
                r.amount, r.payment_id.currency_id, r.payment_id.company_id.currency_id)
            move = r.env['account.move'].create(r._get_move_vals(today_date))
            debit_account_id, credit_account_id = r._get_move_line_accounts()
            amount = r.payment_id.amount
            lines = []
            currency_id = False
            if amount_currency:
                currency_id = r.payment_id.currency_id.id
            lines.append((0, 0, r._get_move_line_vals(debit, credit, amount, currency_id, debit_account_id)))
            lines.append((0, 0, r._get_move_line_vals(credit, debit, amount, currency_id, credit_account_id)))
            move.write({'line_ids': lines})
            move.post()
            last_state_label = dict(r.fields_get(allfields=['state'])['state']['selection'])[r.Last_state]
            state_label = dict(r.fields_get(allfields=['state'])['state']['selection'])[r.state]
            description = "تم التحويل من " + last_state_label + " الي " + state_label

            self.WriteLog(move.id, description, str(today_date))
    # def make_move(self):
    #     for r in self:
    #         today_date = fields.Date.today()
    #         aml = r.env['account.move.line']
    #         debit, credit, ss, amount_currency = aml.with_context(date=r.payment_id.date).compute_amount_fields(r.amount, r.payment_id.currency_id, r.payment_id.company_id.currency_id)
    #         move = r.env['account.move'].create(r._get_move_vals(today_date))
    #
    #         debit_account_id, credit_account_id = r._get_move_line_accounts()
    #         amount = r.payment_id.amount
    #         lines = []
    #         currency_id = False
    #         if amount_currency:
    #             currency_id = r.payment_id.currency_id.id
    #         lines.append((0, 0, r._get_move_line_vals(debit, credit, amount_currency, currency_id, debit_account_id)))
    #         lines.append((0, 0, r._get_move_line_vals(credit, debit, amount_currency, currency_id, credit_account_id)))
    #         move.write({'line_ids': lines})
    #         move.post()
    #         last_state_label = dict(r.fields_get(allfields=['state'])['state']['selection'])[r.Last_state]
    #         state_label = dict(r.fields_get(allfields=['state'])['state']['selection'])[r.state]
    #         description = "تم التحويل من " + last_state_label + " الي " + state_label
    #
    #         self.WriteLog(move.id, description, str(today_date))

    #######################################
    # Helper functions to create the move #
    #######################################
    def _get_move_vals(self, move_date):
        """ Return dict to create the check move
        """
        self.ensure_one()
        if self.payment_id:
            return {
                # 'name': name,
                'date': move_date,
                'ref': self.name,
                'company_id': self.payment_id.company_id.id,
                'journal_id': self.payment_id.journal_id.id,
                # 'partner_id': self.payment_id.partner_id and self.payment_id.partner_id.id or False,
            }

    def _get_move_line_vals(self, debit, credit, amount_currency, currency_id, account_id, name=''):
        self.ensure_one()
        return {
            'name': name and name or self.name,
            'credit': credit,
            'debit': debit,
            'account_id': account_id,
            'currency_id': currency_id,
            'amount_currency': debit > 0 and amount_currency or -amount_currency,
            'partner_id': self.payment_id.partner_id.id,
        }

    ##########################################
    # ///Helper functions to create the move #
    ##########################################

    def make_a_returning_payment(self, communication=''):
        self.ensure_one()

        today = fields.Date.today()
        payment_dict = {
            'payment_date': today,
            'payment_reference': self.payment_id.payment_reference,
            'ref': communication and communication or self.payment_id.ref,
        }

        payment_context = {
            'check_payment': True,
            'check_last_state': self.Last_state,
            'check_state': self.state,
        }

        if self.type == 'transfer':
            payment_context.update(change_account_in_aml_to_out_standing=True)
            payment_dict.update(payment_type='transfer')
            payment_dict.update(journal_id=self.payment_id.destination_journal_id.id)
            payment_dict.update(destination_journal_id=self.payment_id.journal_id.id)
            payment_context.update(journal_id_to_change=self.payment_id.journal_id.id)
        elif self.Last_state in ['out_standing', 'rdv']:
            payment_dict.update(payment_type='inbound')
        elif self.Last_state in ['under_collection', 'rdc']:
            payment_dict.update(payment_type='outbound')

        payment = self.payment_id.copy(payment_dict)
        payment.with_context(payment_context).action_post()
        for line in payment.move_id.line_ids:
            if not line.ref:
                line.ref = self.name

        last_state_label = dict(self.fields_get(allfields=['state'])['state']['selection'])[self.Last_state]
        state_label = dict(self.fields_get(allfields=['state'])['state']['selection'])[self.state]
        description = "تم التحويل من" + last_state_label + " الي " + state_label

        self.WriteLog(payment.move_id.line_ids[0].move_id.id, description, str(today), payment_id=payment.id)

    def _get_move_line_accounts(self):
        self.ensure_one()
        if self.type == 'inbound':
            # Customer part
            if self.state == 'in_bank' and self.Last_state == 'under_collection':
                return self.to_account_journal_id.default_account_id.id, self.company_id.account_journal_payment_debit_account_id.id
            if self.state == 'rdc' and self.Last_state == 'under_collection':
                return self.payment_id.journal_id.rdc.id, self.company_id.account_journal_payment_debit_account_id.id
            elif self.state == 'under_collection' and self.Last_state == 'rdc':
                return self.company_id.account_journal_payment_debit_account_id.id, self.payment_id.journal_id.rdc.id
            elif self.state == 'rdc' and self.Last_state == 'in_bank':
                return self.payment_id.journal_id.rdc.id, self.to_account_journal_id.default_account_id.id
            elif self.state == 'in_bank' and self.Last_state == 'rdc':
                return self.to_account_journal_id.default_account_id.id, self.payment_id.journal_id.rdc.id
            elif self.state == 'return_acc' and self.Last_state == 'rdc':
                return self.account_holder.property_account_receivable_id.id, self.payment_id.journal_id.rdc.id
            elif self.state == 'return_acc' and self.Last_state == 'under_collection':
                return self.account_holder.property_account_receivable_id.id, self.company_id.account_journal_payment_debit_account_id.id
            elif self.state == 'return_acc' and self.Last_state == 'in_bank':
                return self.account_holder.property_account_receivable_id.id, self.to_account_journal_id.default_account_id.id
            else:
                _logger.error('can not determine move accounts for {} with state = {}, Last_state = {}. this is unknown change in the state!'.format(self, self.state, self.Last_state))
                raise ValidationError("Unknown check state changes!\nFrom '{}' to '{}'".format(
                    self.Last_state or '', self.state or ''
                ))

        elif self.type in ['outbound', 'transfer']:
            # Vendor Part
            if self.payment_id:
                if self.state == 'withdrawal' and self.Last_state == 'out_standing':
                    return self.payment_id.journal_id.default_account_id.id, self.payment_id.journal_id.default_account_id.id
                elif self.state == 'rdv' and self.Last_state == 'out_standing':
                    return self.payment_id.journal_id.default_account_id.id, self.payment_id.journal_id.rdv.id
                elif self.state == 'rdv' and self.Last_state == 'withdrawal':
                    return self.payment_id.journal_id.default_account_id.id, self.payment_id.journal_id.rdv.id
                elif self.state == 'withdrawal' and self.Last_state == 'rdv':
                    return self.payment_id.journal_id.rdv.id, self.payment_id.journal_id.default_account_id.id
                elif self.state == 'return_acv' and self.Last_state == 'rdv':
                    return self.payment_id.journal_id.rdv.id, self.payment_id.partner_id.property_account_payable_id.id
                elif self.state == 'return_acv' and self.Last_state == 'out_standing':
                    return self.payment_id.journal_id.default_account_id.id, self.payment_id.partner_id.property_account_payable_id.id
                else:
                    _logger.error('can not determine move accounts for {} with state = {}, Last_state = {}. this is unknown change in the state!'.format(self, self.state, self.Last_state))
                    raise ValidationError("Unknown check state changes!\nFrom '{}' to '{}'".format(
                        self.Last_state or '', self.state or ''
                    ))
        else:
            _logger.error('can not determine move accounts for {} with type = {}. type should be either "inbound" or "outbound"'.format(self, self.type))
            raise ValidationError('Error while calculating accounts for check move!')

    @api.model
    def create(self, vals):
        if vals['type'] == 'inbound':
            vals['name'] = self.env['ir.sequence'].get('check_followups.check_followups')
        else:
            vals['name'] = self.env['ir.sequence'].get('check_followups.check_followups_vender')
        return super(CheckFollowups, self).create(vals)

    def unlink(self):
        raise UserError('You Cannot Delete The Check')

    def WriteLog(self, Move_id, Description, date, payment_id=False):
        self.ensure_one()
        log = {
            'move_id': Move_id,
            'name': Description,
            'date': date,
            'Check': self.id,
            'payment_id': payment_id,
        }
        return self.env['check_followups.checklogs'].create(log)


class Partner(models.Model):
    _inherit = 'res.partner'

    # Bank_Account_ids = fields.One2many('partner.bank.account', 'Partner_Id')
    check_ids = fields.One2many('check_followups.check_followups', 'account_holder')
    property_account_check_id = fields.Many2one(
        comodel_name="account.account",
        string="Checks Account",
        domain=[("deprecated", "=", False)],
        help="Account used for Check Under Collection",
    )

    def action_view_checks(self):
        '''
        This function returns an action that display existing Checks
        of given Customer ids. It can either be a in a list or in a form
        view, if there is only one Check to show.
        '''

        action = self.env.ref('ii_simple_check_management.check_followups_customer').read()[0]
        checks = self.mapped('check_ids')
        if len(checks) > 1:
            action['domain'] = [('id', 'in', checks.ids)]
        elif checks:
            action['views'] = [(self.env.ref('ii_simple_check_management.check_followups_customerformview').id, 'form')]
            action['res_id'] = checks.id
        return action


class bank_res(models.Model):
    _inherit = 'res.bank'

    amount_textx = fields.Integer('Amount in Text X-axis')
    amount_texty = fields.Integer('Amount in Text Y-axis')
    acc_holderx = fields.Integer('Account Holder X-axis')
    acc_holdery = fields.Integer('Account Holder Y-axis')
    datex = fields.Integer('Date X-axis')
    datey = fields.Integer('Date Y-axis')
    amountx = fields.Integer('Amount X-axis')
    amounty = fields.Integer('Amount Y-axis')
    account_holder_width = fields.Integer('Name Width')
    money_text_width = fields.Integer('Money Area Width')
    money_text_height = fields.Integer('Money Area Height')


class JournalAccount(models.Model):
    _inherit = 'account.journal'

    under_collection = fields.Many2one('account.account')
    rdc = fields.Many2one('account.account', 'Return Checks')
    ################################### Customer accounts
    out_standing = fields.Many2one('account.account')
    rdv = fields.Many2one('account.account', 'Return Checks')
    ################################### Vender accounts
    Check_no = fields.Integer('Check No')


class CheckLogs(models.Model):
    _name = 'check_followups.checklogs'

    move_id = fields.Many2one('account.move', string='Move')
    name = fields.Char('Description')
    date = fields.Date('Date')
    Check = fields.Many2one('check_followups.check_followups')
    payment_id = fields.Many2one('account.payment', 'Payment')
