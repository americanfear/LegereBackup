from odoo import fields, models
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    state = fields.Selection(selection_add=[('to_approve', 'To Approve'), ('posted',)],
                             ondelete={"to_approve": "set default"})

    next_approval_id = fields.Many2one(
        string="Next Approval",
        comodel_name='account.approver',
        store=True, readonly=True, ondelete='restrict',
        tracking=True,
        check_company=True
    )

    def get_next_approval(self, prev_id, amt):
        approvals = self.env['account.approver'].search(
            [('approval_type', '=', 'bill')], order="sequence asc")
        found_prev = not prev_id
        next_approval = None
        for approval in approvals:
            if not found_prev and approval.id == prev_id.id:
                found_prev = True
            elif found_prev and amt >= approval.min_amount and (amt <= approval.max_amount or approval.max_amount == 0):
                next_approval = approval
                break
        return next_approval

    def approval_attempt(self, prev_id, amt):
        amt = amt if amt else self.amount_total
        is_approver = False
        get_next_approval = False
        next_approval = prev_id or self.next_approval_id
        approvals = self.env['account.approver'].search(
            [('approval_type', '=', 'bill')], order="sequence asc")
        for approval in approvals:
            if get_next_approval:
                next_approval = approval
                get_next_approval = False
            if self.env.user == approval.name and (amt <= approval.max_amount or approval.max_amount == 0):
                is_approver = True
                next_approval = False
                get_next_approval = True

        return {
            "result": is_approver,
            "next_approval": next_approval,
        }

    def send_approval_request(self):
        if self.next_approval_id:
            template = self.env.ref('legere_nacha_approvals.email_template_account_approval_request', raise_if_not_found=False)
            if template:
                template.send_mail(self.id)

    def send_approval_notice(self):
        template = self.env.ref('legere_nacha_approvals.email_template_account_approval_request_approved', raise_if_not_found=False)
        if template:
            template.send_mail(self.id)

    def write(self, vals):
        _logger.warning(f'DEBUG>>> ACCOUNT MOVE WRITE self:{self}, vals:{vals}')
        needs_approval_notice = {}
        # TODO: If accept multiple, does it make sense to set next_approval_id and state for all???
        for acct_move in self:
            new_state = "state" in vals and vals["state"]
            _logger.warning(f'DEBUG>>> move_type:{acct_move.move_type}, new_state:{new_state}')
            # If Vendor Bill and not internal change of Next Approval or state change to To Approve
            if acct_move.move_type == "in_invoice" and "next_approval_id" not in vals and new_state != "to_approve":
                next_amt = vals["amount_total"] if "amount_total" in vals else acct_move.amount_total
                new_approval = acct_move.get_next_approval(False, next_amt)
                approval_target = acct_move.next_approval_id or new_approval
                # If no Next Approval and it is not set before, ignore
                if not approval_target:
                    if acct_move.next_approval_id:
                        vals["next_approval_id"] = False
                # If amount_total is changing with this request, recalc Next Approval and move to Draft
                elif next_amt != acct_move.amount_total:
                    # Recalculate next approval with amount change
                    # ❓ Could only restart approval if the amount is more than before
                    vals["next_approval_id"] = new_approval
                    if new_state != "draft":
                        vals["state"] = "draft"
                # If new state is draft, reset the Next Approval
                elif new_state == "draft":
                    vals["next_approval_id"] = new_approval
                # If new state is posted, try to approve the Bill
                elif new_state == "posted":
                    attempt_result = acct_move.approval_attempt(approval_target, next_amt)
                    # If the current user is an approver
                    if attempt_result["result"]:
                        next_approval = attempt_result["next_approval"]
                        if next_approval and next_approval.sequence <= acct_move.next_approval_id.sequence:
                            raise UserError("This bill payment is awaiting the next level of approval.")
                        elif next_approval:
                            needs_approval_notice[acct_move.id] = True
                            vals["state"] = "to_approve"
                            vals["next_approval_id"] = next_approval
                        else:
                            # Only send notice if the current approver is NOT the original creator
                            if self.env.user != acct_move.create_uid:
                                acct_move.send_approval_notice()
                            vals["next_approval_id"] = False
                    # If the current user is not an approver but approval is needed
                    elif attempt_result["next_approval"]:
                        # If it is already in To Approve, then reject the attempt
                        if acct_move.state == "to_approve":
                            raise UserError("You are not authorized to approve this payment.")
                        # Otherwise it is someone posting it initially, so set to To Approve
                        else:
                            needs_approval_notice[acct_move.id] = True
                            vals["state"] = "to_approve"
                            vals["next_approval_id"] = attempt_result["next_approval"]
                # If canceling the Bill, clear the Next Approval field
                elif new_state == "cancel":
                    if acct_move.next_approval_id:
                        vals["next_approval_id"] = False
                # Otherwise, update the Next Approval if moving to Draft or if it is remaining in Draft or To Approve
                elif new_state == "draft" or (not new_state and acct_move.state in ["draft", "to_approve"]):
                    if acct_move.next_approval_id != new_approval:
                        vals["next_approval_id"] = new_approval

        super().write(vals)
        # move = super().write(vals)
        # Only send approval request in To Approve stage
        for move in self:
            if needs_approval_notice and move.id in needs_approval_notice and move.state == "to_approve" and (
                move.next_approval_id and not move.next_approval_id.ignore_notification
            ):
                move.send_approval_request()
        return
