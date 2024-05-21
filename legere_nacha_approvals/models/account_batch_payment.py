from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import base64
import math

class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    @api.depends('approver_ids', 'approver_ids.state')
    def _check_pending_approval(self):
        for record in self:
            record.is_approval_pending = False
            if record.approver_ids.filtered(lambda p: p.state in ['to_approve', 'rejected']):
                record.is_approval_pending = True

    def _compute_approver(self):
        for record in self:
            record.is_current_approver = (record.current_approval_id and record.current_approval_id.name == self.env.user) \
                                        or self.env.is_superuser()

    @api.depends('approver_ids', 'approver_ids.state')
    def _get_current_approval(self):
        for record in self:
            current_approval = self.env['payment.approver'].search([('batch_payment_id', '=', record.id),
                ('state', 'in', ['to_approve', 'rejected'])], order='sequence', limit=1)
            record.current_approval_id = current_approval and current_approval.id or False

    approver_ids = fields.One2many('payment.approver', 'batch_payment_id', string='Approvers', readonly=True)
    is_approval_pending = fields.Boolean(compute='_check_pending_approval', string='Is Approval Pending?', readonly=True, store=True)
    current_approval_id = fields.Many2one('payment.approver', string='Current Approval', compute='_get_current_approval', readonly=True, store=True)
    is_current_approver = fields.Boolean(string='Is Current Approver', compute='_compute_approver')
    approval_request_sent = fields.Boolean(string='Approval Request Sent', related='current_approval_id.approval_request_sent', readonly=True, store=True)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True, default=lambda self: self.env.uid)

    def validate_batch(self):
        if self.payment_method_code == 'nacha' and self.approver_ids.filtered(lambda x: x.state != 'approved'):
            return False
        return super(AccountBatchPayment, self).validate_batch()

    def create_approver_lines(self):
        self.current_approval_id = False
        payment_approver_pool = self.env['payment.approver']
        for record in self.filtered(lambda x: x.state == 'draft' and x.payment_method_code == 'nacha'):
            record.approver_ids.unlink()
            approval_templates = self.env['payment.approval.template'].search([('approval_type', '=', 'batch_payment'),
                                                                      ('min_amount', '<=', abs(record.amount)),
                                                                      ('company_id', '=', self.env.company.id)], order='sequence')
            for approval in approval_templates:
                payment_approver_pool.create({'sequence': approval.sequence,
                                                 'name': approval.name.id,
                                                 'batch_payment_id': record.id,
                                                 'min_amount': approval.min_amount,
                                                 'max_amount': approval.max_amount,
                                                 'company_id': approval.company_id.id,
                                                 'state': 'to_approve'})

    @api.model_create_multi
    def create(self, vals_list):
        rec = super(AccountBatchPayment, self).create(vals_list)
        for record in rec.filtered(lambda x: x.payment_method_code == 'nacha'):
            record.approver_ids.unlink()
            record.create_approver_lines()
        return rec

    def write(self, vals):
        if vals.get('payment_method_id'):
            for record in self:
                record.approver_ids.unlink()
        current_amount = 0.0
        new_amount = 0.0
        for record in self:
            current_amount = record.amount
        res = super(AccountBatchPayment, self).write(vals)
        for record in self:
            new_amount = record.amount
        if current_amount != new_amount:
            for record in self.filtered(lambda x: x.payment_method_code == 'nacha'):
                record.approver_ids.unlink()
                record.create_approver_lines()
        return res

    def action_approve(self):
        for record in self:
            record.message_post(body=_('Batch payment approved by %s') % record.current_approval_id.name.name)
            record.current_approval_id.state = 'approved'
            record._get_current_approval()
            if record.current_approval_id:
                record.send_approval_request()
            else:
                partner = record.user_id.partner_id if record.user_id else record.create_uid.partner_id
                record.message_post_with_view(
                    'legere_nacha_approvals.batch_payment_approve',
                    composition_mode='mass_mail',
                    partner_ids=[(4, partner.id)],
                    auto_delete=True,
                    auto_delete_message=True,
                    parent_id=False,
                    subtype_id=self.env.ref('mail.mt_note').id)

    def action_reject(self):
        for record in self:
            record.current_approval_id.state = 'rejected'

    def action_request_for_approve(self):
        for record in self:
            record.send_approval_request()

    def send_approval_request(self):
        for record in self:
            record.current_approval_id.approval_request_sent = True
            record.current_approval_id.state = 'to_approve'
            template = self.env.ref('legere_nacha_approvals.email_template_batch_payment_request_for_approval', raise_if_not_found=False)
            if template:
                template.send_mail(self.id)

    # CUSTOM: Copied and updated from /l10n_us_payment_nacha/models/account_batch_payment.py
    def _generate_nacha_batch_header_record(self, payment, batch_nr):
        batch = []
        batch.append("5")  # Record Type Code
        batch.append("220")  # Service Class Code (credits only)
        batch.append("{:16.16}".format(self.journal_id.company_id.name))  # Company Name
        # Start CUSTOM: Added support for Company Discretionary Data (optional) used by Chase
        disc_data = self.journal_id.legere_nacha_discretionary_data
        batch.append("{:20.20}".format(disc_data.zfill(20) if disc_data else ""))  # Company Discretionary Data (optional)
        # End CUSTOM
        batch.append("{:0>10.10}".format(self.journal_id.nacha_company_identification))  # Company Identification
        batch.append("PPD")  # Standard Entry Class Code
        batch.append("{:10.10}".format(payment.ref))  # Company Entry Description
        batch.append("{:6.6}".format(payment.date.strftime("%y%m%d")))  # Company Descriptive Date
        batch.append("{:6.6}".format(payment.date.strftime("%y%m%d")))  # Effective Entry Date
        batch.append("{:3.3}".format(""))  # Settlement Date (Julian)
        batch.append("1")  # Originator Status Code
        batch.append("{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Originating DFI Identification
        batch.append("{:07d}".format(batch_nr))  # Batch Number

        return "".join(batch)
