from odoo import api, fields, models
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    payment_transactions_batch_id = fields.Many2one('payment.transactions.batch', string='Payment Transactions Batch')

class PaymentTransactionsBatch(models.Model):
    _name = 'payment.transactions.batch'
    _description = 'Payment Transactions Batch'
    _rec_name = 'BatchNumber'
    _order = 'SubmitDate desc, id desc'

    def _get_transaction_count(self):
        for record in self:
            record.transaction_count = len(self.env['payment.transaction'].search([('payment_transactions_batch_id', '=', record.id)]))

    def action_view_transaction(self):
        action = self.env['ir.actions.act_window']._for_xml_id('payment.action_payment_transaction')
        action['domain'] = [('payment_transactions_batch_id', '=', self.id)]
        return action

    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.payment_transaction_ids.mapped('amount'))

    @api.depends('payment_transaction_ids', 'payment_transaction_ids.amount', 'fee_amount', 'chargeback_amount', 'adjustment_amount')
    def _compute_deposit_amount(self):
        for record in self:
            #record.deposit_amount = sum(record.payment_transaction_ids.mapped('amount')) + record.fee_amount + record.chargeback_amount + record.adjustment_amount
            record.deposit_amount = sum(record.payment_transaction_ids.mapped('amount')) + record.fee_amount + record.adjustment_amount

    BatchNumber = fields.Char(string='Batch Number', required=True)
    SubmitDate = fields.Datetime(string='Batch Date', required=False)
    State = fields.Char(string='State')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    transaction_count = fields.Integer(compute="_get_transaction_count")
    payment_transaction_ids = fields.One2many('payment.transaction', 'payment_transactions_batch_id', string='Payment Transactions')
    amount_total = fields.Monetary(string='Total', compute='_compute_amount_total')
    payment_provider_id = fields.Many2one('payment.provider', string='Provider')
    fee_amount = fields.Monetary(string='Fee Amount')
    chargeback_amount = fields.Monetary(string='Chargeback Amount')
    adjustment_amount = fields.Monetary(string='Adjustment Amount')
    deposit_amount = fields.Monetary(string='Deposit Amount', compute='_compute_deposit_amount')

    def check_payment_transaction(self, transaction_ID, amount, batch_id):
        payment_transaction_pool = self.env['payment.transaction']
        payment_transaction_id = payment_transaction_pool.search([('provider_reference', '=', transaction_ID),
            ('amount', '=', amount)], limit=1)
        if payment_transaction_id:
            payment_transaction_id.write({'payment_transactions_batch_id': batch_id.id})
            return True
        else:
            return False

    @api.model
    def import_payment_transactions_batch(self):
        for record in self.env['payment.provider'].search([('import_transactions_batch', '!=', False), ('state', '!=', 'disabled')]):
            if hasattr(self.env['payment.transactions.batch'], '%s_import_payment_transactions_batch' % record.code):
                try:
                    getattr(self.env['payment.transactions.batch'], '%s_import_payment_transactions_batch' % record.code)(record=record)
                except Exception as e:
                    _logger.info("%s", str(e))
