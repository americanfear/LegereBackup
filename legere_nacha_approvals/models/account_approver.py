from odoo import fields, models


class AccountApprover(models.Model):
    _name = "account.approver"
    _description = "Account Approver"
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
        If Total Amount is greater than Maximum Amount then the approver will be skipped.
        If the Maximum Amount is 0 then it has no maximum.""")
    approval_type = fields.Selection([('bill', 'Bill')], default='bill', string='Approval Type', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency',
                                          related='company_id.currency_id', readonly=True,
                                          help='Utility field to express threshold currency')
    ignore_notification = fields.Boolean(
        string="Ignore Notification",
        help="""No email notification will be sent to this approver.  
        It is assumed they will receive a separate notification somehow."""
    )
    _sql_constraints = [
        ('sequence_uniq', 'unique(sequence, company_id)', 'Sequence must be unique per company!'),
    ]