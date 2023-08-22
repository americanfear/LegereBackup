from odoo import _, api, fields, models

class PaymentPayment(models.Model):
    _inherit = 'account.payment'

    def _compute_check_available_refund(self):
        for record in self:
            record.check_available_refund = False if not record.payment_transaction_id or not record.payment_transaction_id.provider_id or record.payment_transaction_id.provider_code not in ['stride', 'payengine'] or record.payment_transaction_id.amount <= 0.0 or record.payment_transaction_id.pending_refund_amount <= 0.0 else True

    check_available_refund = fields.Boolean(string='Check Available Refund', compute='_compute_check_available_refund')

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _compute_pending_refund_amount(self):
        for record in self:
            refund_amount = sum(self.env['payment.transaction'].search([
                ('source_transaction_id', '=', record.id), ('state', 'in', ['authorized', 'done'])
            ]).mapped('amount'))
            record.pending_refund_amount = (record.amount + refund_amount)

    pending_refund_amount = fields.Float(string="Pending Refund Amount", compute='_compute_pending_refund_amount')