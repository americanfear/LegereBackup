from odoo import _, api, fields, models

import logging
_logger = logging.getLogger(__name__)

class StridePaymentTransactionRefund(models.TransientModel):
    _name = 'stride.payment.transaction.refund'
    _description = 'Create Stride Payment Transaction Refund'

    refund_type = fields.Selection([('full_amount', 'Full Amount'), ('partial', 'Partial')], string="Refund Type", default="full_amount", required=True)
    transaction_id = fields.Many2one('payment.transaction', string="Payment Transaction", required=True)
    refund_amount = fields.Monetary(string="Amount to refund", currency_field='currency_id', required=True)
    pending_refund_amount = fields.Monetary(string="Pending Amount to refund", currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one(string="Currency", comodel_name='res.currency', required=True)

    @api.onchange('refund_type')
    def onchange_refund_type(self):
        """This function returns value of  product's member price based on product id.
        """
        if self.refund_type == 'full_amount':
            self.refund_amount = self.pending_refund_amount

    @api.model
    def default_get(self, fields):
        res = super(StridePaymentTransactionRefund, self).default_get(fields)
        if self.env.context.get('active_id'):
            if self.env.context.get('active_model') == 'payment.transaction':
                transaction_id = self.env['payment.transaction'].browse(self.env.context.get('active_id'))
            if self.env.context.get('active_model') == 'account.payment':
                transaction_id = self.env['account.payment'].browse(self.env.context.get('active_id')).payment_transaction_id
            res['transaction_id'] = transaction_id.id
            res['pending_refund_amount'] = transaction_id.pending_refund_amount or 0.0
            res['refund_amount'] = transaction_id.pending_refund_amount or 0.0
            res['currency_id'] = transaction_id.currency_id.id
        return res

    def do_process_refund(self):
        if hasattr(self.env['stride.payment.transaction.refund'], '%s_do_process_refund' % self.transaction_id.provider_id.code):
            return getattr(self, '%s_do_process_refund' % self.transaction_id.provider_id.code)()