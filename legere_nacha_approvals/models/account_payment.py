from odoo import fields, models, api
from odoo.exceptions import UserError
# import logging
# _logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_payment_approval_rejected = fields.Boolean(
        string="Is Payment Approval Rejected",
        store=True,
        readonly=True,
        tracking=True,
    )

    next_approval_id = fields.Many2one(
        string="Next Approval",
        comodel_name='payment.approval.template',
        store=True, readonly=True, ondelete='restrict',
        tracking=True,
        check_company=True
    )

    def get_next_approval(self, prev_id, amt):
        approvals = self.env['payment.approval.template'].search(
            [('approval_type', '=', 'payment')], order="sequence asc")
        found_prev = not prev_id
        next_approval = None
        for approval in approvals:
            if not found_prev and approval.id == prev_id.id:
                found_prev = True
            elif found_prev and amt >= approval.min_amount and (amt <= approval.max_amount or approval.max_amount == 0):
                next_approval = approval
                break
        return next_approval

    # Check if an approver for this payment.
    # Return result and next approval needed or same (if unchanged)
    def attempt_approval(self):
        is_approver = False
        get_next_approval = False
        next_approval = self.next_approval_id
        approvals = self.env['payment.approval.template'].search(
            [('approval_type', '=', 'payment')], order="sequence asc")
        for approval in approvals:
            if get_next_approval:
                next_approval = approval
                get_next_approval = False
            if self.env.user == approval.name and (self.amount <= approval.max_amount or approval.max_amount == 0):
                is_approver = True
                next_approval = None
                get_next_approval = True

        return {
            "result": is_approver,
            "next_approval": next_approval,
        }

    def action_post(self):
        self.next_approval_id = False
        self.is_payment_approval_rejected = False
        super().action_post()

    def action_cancel(self):
        self.next_approval_id = False
        self.is_payment_approval_rejected = False
        super().action_cancel()

    def action_legere_approve(self):
        if self.next_approval_id:
            attempt_result = self.attempt_approval()
            if attempt_result["result"]:
                next_approval = attempt_result["next_approval"]
                if next_approval and next_approval.sequence <= self.next_approval_id.sequence:
                    raise UserError("This payment is awaiting the next level of approval.")
                elif next_approval:
                    self.next_approval_id = next_approval
                    self.send_approval_request()
                else:
                    self.action_post()
                    self.send_approval_notice()
            else:
                raise UserError("You are not authorized to approve this payment.")

    def action_legere_reject(self):
        if self.next_approval_id:
            attempt_result = self.attempt_approval()
            # If the user is any approver, than allow them to reject the payment
            if attempt_result["result"]:
                self.is_payment_approval_rejected = True
                self.send_reject_notice()
            else:
                raise UserError("You are not authorized to reject this payment.")

    def action_legere_restart(self):
        # Restart approval process
        self.next_approval_id = self.get_next_approval(False, self.amount)
        self.is_payment_approval_rejected = False
        if self.next_approval_id:
            self.send_approval_request()

    def send_approval_request(self):
        if self.next_approval_id:
            template = self.env.ref('legere_nacha_approvals.email_template_payment_request_for_approval', raise_if_not_found=False)
            if template:
                template.send_mail(self.id)

    def send_reject_notice(self):
        if self.next_approval_id:
            template = self.env.ref('legere_nacha_approvals.email_template_payment_rejected_notice', raise_if_not_found=False)
            if template:
                template.send_mail(self.id)

    def send_approval_notice(self):
        template = self.env.ref('legere_nacha_approvals.email_template_payment_approved_notice', raise_if_not_found=False)
        if template:
            template.send_mail(self.id)

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        for payment in payments:
            if payment.state == "draft":
                next_approval = payment.get_next_approval(payment.next_approval_id, payment.amount)
                if next_approval:
                    payment.write({
                        "next_approval_id": next_approval,
                    })
                    payment.send_approval_request()
        return payments

    def write(self, vals):
        # Change vals to reset if the amount is changed (vals amount differs from self amount)
        needs_approval = False
        if self.state == "draft" and "next_approval_id" not in vals and (
                "amount" in vals and vals["amount"] != self.amount
        ):
            next_approval = self.get_next_approval(False, vals["amount"])
            needs_approval = bool(next_approval)
            vals["next_approval_id"] = next_approval
            vals["is_payment_approval_rejected"] = False
        payment = super().write(vals)
        if needs_approval:
            self.send_approval_request()
        return payment
