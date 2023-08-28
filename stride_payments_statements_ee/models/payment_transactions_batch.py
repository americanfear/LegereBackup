import pytz
import logging
from odoo import api, fields, models,_
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class PaymentTransactionsBatch(models.Model):
    _inherit = 'payment.transactions.batch'

    account_bank_statement_id = fields.Many2one('account.bank.statement', string='Account Bank Statement')
    is_reconciled = fields.Boolean()
    
    def transaction_batch_create_bank_statement(self):
        for record in self.search([('account_bank_statement_id', '=', False),('is_reconciled', '=', False)]).filtered(lambda x: x.payment_transaction_ids):
            record.action_create_bank_statement()

    def action_create_bank_statement(self):
        account_bank_statement_line_pool = self.env['account.bank.statement.line']
        for record in self:
            journal_id = record.payment_transaction_ids.filtered(lambda x: x.provider_id)[0].provider_id.journal_id 
            account_bank_statement_id = self.env['account.bank.statement'].create({'date': record.SubmitDate and record.SubmitDate.date() or fields.Date.today(),
                'name': "batch_"+record.BatchNumber+"_statement",
                'journal_id': journal_id.id,
                'balance_start': 0.0,
                'balance_end_real': 0.0})
            
            amount_without_payment = sum(record.payment_transaction_ids.filtered(lambda x: not x.payment_id).mapped('amount'))
            amount_without_payment_des = ', '.join([o.reference for o in record.payment_transaction_ids.filtered(lambda x: not x.payment_id)])
            SubmitDate_tz = pytz.utc.localize(record.SubmitDate).astimezone(pytz.timezone(self.env.user.tz or 'UTC')) if record.SubmitDate else False
            if amount_without_payment > 0.0:
                account_bank_statement_line_pool.create({'date': SubmitDate_tz and SubmitDate_tz.date() or fields.Date.today(),
                    'journal_id': journal_id.id,
                    'partner_id': False,
                    'payment_ref': amount_without_payment_des,
                    'statement_id': account_bank_statement_id.id,
                    'amount': amount_without_payment})
            
            for payment_transaction in record.payment_transaction_ids.filtered(lambda x: x.payment_id):
                account_bank_statement_line_pool.create({'date': payment_transaction.last_state_change.date(),
                    'journal_id': journal_id.id,
                    'partner_id': payment_transaction.partner_id.id,
                    'payment_ref': payment_transaction.reference,
                    'statement_id': account_bank_statement_id.id,
                    'amount': payment_transaction.amount})

            account_bank_statement_line_pool.create({'date': SubmitDate_tz and SubmitDate_tz.date() or fields.Date.today(),
                'journal_id': journal_id.id,
                'partner_id': False,
                'payment_ref': 'transfer',
                'statement_id': account_bank_statement_id.id,
                'amount': -record.deposit_amount})
            record.write({'account_bank_statement_id': account_bank_statement_id.id})
            
    def action_view_bank_statement(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_bank_statement_tree')
        action['res_id'] = self.account_bank_statement_id.id
        return action