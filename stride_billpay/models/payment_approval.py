from odoo import fields, models, api


class PaymentApprovalTemplate(models.Model):
    _name = "payment.approval.template"
    _description = "Payment Approval Template"
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Many2one('res.users', string='Approver', required=True)
    min_amount = fields.Monetary(
        string='Minimum Amount',
        currency_field='company_currency_id', required=True,
        help="""Minimum Amount (included) for which a validation by approver is required.
        If Total Amount is less than Minimum Amount then the approver will be skipped.""")
    max_amount = fields.Monetary(
        string='Maximum Amount',
        currency_field='company_currency_id', required=True,
        help="""Maximum Amount (included) for which a validation by approver is required. 
        If Total Amount is greater than Maximum Amount then the approver will be skipped.""")
    approval_type = fields.Selection([('payment', 'Payment')], default='payment', string='Approval Type', required=True)
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency',
        related='company_id.currency_id', readonly=True, help='Utility field to express threshold currency')
    
    _sql_constraints = [
        ('sequence_uniq', 'unique(sequence, company_id)', 'Sequence must be unique per company!'),
    ]

class PaymentApprover(models.Model):
    _name = "payment.approver"
    _description = "Payment Approver"
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Many2one('res.users', string='Approver', required=True)
    state = fields.Selection([('to_approve', 'To Approve'),
                              ('approved', 'Approved'),
                              ('rejected', 'Rejected')], string='Status', readonly=True, required=True, default='to_approve')
    min_amount = fields.Monetary(string='Minimum Amount', currency_field='company_currency_id')
    max_amount = fields.Monetary(string='Maximum Amount', currency_field='company_currency_id')
    company_id = fields.Many2one('res.company', string='Company')
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', related='company_id.currency_id')
    approval_request_sent = fields.Boolean(string='Approval Request Sent')