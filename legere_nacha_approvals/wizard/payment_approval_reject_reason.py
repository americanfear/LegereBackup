from odoo import api, fields, models, _

class PaymentApprovalRejectReason(models.TransientModel):
    _inherit = "payment.approval.reject.reason"

    batch_payment_id = fields.Many2one('account.batch.payment', string='Batch Payment')
    
    @api.model
    def default_get(self, fields):
        result = super(PaymentApprovalRejectReason, self).default_get(fields)
        if self._context.get('active_model') == 'account.batch.payment' and self._context.get('active_id', False):
            result['batch_payment_id'] = self._context.get('active_id', False)
        return result

    def action_submit_reason(self):
        if self.batch_payment_id:
            self.batch_payment_id.current_approval_id.state = 'rejected'
            self.batch_payment_id.current_approval_id.approval_request_sent = False
            partner = self.batch_payment_id.user_id.partner_id if self.batch_payment_id.user_id else self.batch_payment_id.create_uid.partner_id
            self.batch_payment_id.message_post_with_view(
                'legere_nacha_approvals.batch_payment_reject',
                composition_mode='mass_mail',
                values={'reason': self.reason},
                partner_ids=[(4, partner.id)],
                auto_delete=True,
                auto_delete_message=True,
                parent_id=False,
                subtype_id=self.env.ref('mail.mt_note').id)
        else:
            return super(PaymentApprovalRejectReason, self).action_submit_reason()