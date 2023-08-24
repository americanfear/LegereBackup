from odoo import fields, models, api

class PaymentApprovalTemplate(models.Model):
    _inherit = "payment.approval.template"

    approval_type = fields.Selection(
        selection_add=[('batch_payment', 'Batch Payment')], ondelete={'batch_payment': 'set default'}, default='batch_payment')

class PaymentApprover(models.Model):
    _inherit = "payment.approver"

    batch_payment_id = fields.Many2one('account.batch.payment', string='Batch Payment', ondelete='cascade')