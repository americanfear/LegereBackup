from odoo import api, fields, models, _

class PaymentApprovalRejectReason(models.TransientModel):
    _name = "payment.approval.reject.reason"
    _description = "Payment Approval Reject Reason"

    reason = fields.Text('Reason', required=True)

    def action_submit_reason(self):
        return