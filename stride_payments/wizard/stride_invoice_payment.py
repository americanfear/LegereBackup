from odoo import _, api, fields, models

import logging
_logger = logging.getLogger(__name__)

class StrideInvoicePayment(models.TransientModel):
    _name = 'stride.invoice.payment'
    _description = 'Stride Invoice Payment'

    @api.depends('invoice_ids')
    def _get_partner(self):
        for record in self:
            record.partner_id = record.invoice_ids and record.invoice_ids[0].partner_id.id or False

    @api.depends('invoice_ids')
    def _get_amount(self):
        for record in self:
            record.amount = sum(record.invoice_ids.mapped('amount_residual'))

    @api.depends('invoice_ids')
    def _get_reference(self):
        for record in self:
            record.reference = ','.join(record.invoice_ids.mapped('name'))

    @api.depends('invoice_ids.partner_id', 'company_id')
    def _get_email(self):
        for record in self:
            email = ''
            if record.invoice_ids[0].partner_id.email and len(record.invoice_ids[0].partner_id.email) <= 39:
                email = record.invoice_ids[0].partner_id.email
            else:
                email = record.company_id.partner_id.email or 'info@yourcompany.com'
            record.email =  email

    partner_id = fields.Many2one('res.partner', string='Partner', compute='_get_partner', store=True)
    amount = fields.Monetary(string='Amount', compute='_get_amount')
    reference = fields.Char(string='Reference', compute='_get_reference')
    invoice_ids = fields.Many2many('account.move', string='Invoices', 
        domain="[('state', '=', 'posted'), ('type', '=', 'out_invoice'), ('invoice_payment_state', '!=', 'paid'), ('partner_id', '=', partner_id)]")
    payment_method = fields.Selection([('card', 'Credit Card'),
        ('bank', 'Bank Account'),
        ('token', 'Token')], default='card', string='Payment Method', required=True)
    payment_token_id = fields.Many2one('payment.token', string='Saved payment token',
        domain="[('partner_id', '=', partner_id)]")
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    provider_id = fields.Many2one('payment.provider', string='Payment Provider', required=False,
        domain="[('state', '!=', 'disabled')]")
    provider_code = fields.Selection(related='provider_id.code')
    email = fields.Char(string='Email', compute='_get_email')
    partner_email = fields.Char(string='Partner Email', related='partner_id.email')
    send_receipt = fields.Boolean(string='Send Receipt', default=True)
    capture_token = fields.Boolean(string='Save payment details', default=True)

    @api.onchange('payment_method')
    def onchange_payment_method(self):
        self.provider_id = False

    @api.onchange('payment_token_id')
    def onchange_payment_token(self):
        self.provider_id = self.payment_token_id.provider_id.id

    def action_register_invoice_payment(self):
        return True

    def action_cancel_invoice_payment(self):
        return True

    def create_payment_transaction(self, partner_id, amount, reference, payment_token_id, provider_id, company_id, currency_id, capture_token=None):
        invoice_ids = self.env['account.move'].browse(self.env.context.get('invoice_ids'))
        payment_provider_id = self.env['payment.provider'].browse(provider_id)
        partner_id = self.env['res.partner'].browse(partner_id)
        reference = self.env['payment.transaction']._compute_reference(
            payment_provider_id.code,
            prefix=reference
        )
        return self.env['payment.transaction'].create({
            'provider_id': payment_provider_id.id,
            'amount': amount,
            'company_id': company_id,
            'currency_id': currency_id,
            'invoice_ids': [(6, 0, invoice_ids.ids)],
            'partner_id': partner_id.id,
            'token_id': payment_token_id,
            'reference': reference,
            'operation': 'online_direct',
            'tokenize': True if capture_token else False,
        })

    def create_account_payment(self, partner_id, amount, reference, payment_token_id, provider_id, company_id, currency_id, payment_transaction_id):
        invoice_ids = self.env['account.move'].browse(self.env.context.get('invoice_ids'))
        payment_provider_id = self.env['payment.provider'].browse(provider_id)
        partner_id = self.env['res.partner'].browse(partner_id)

        payment_method_line_id = payment_provider_id.journal_id.inbound_payment_method_line_ids.filtered(lambda x: x.payment_method_id.code == payment_provider_id.code)
        return self.env['account.payment'].create({
            'amount': amount,
            'company_id': company_id,
            'currency_id': currency_id,
            'journal_id': payment_provider_id.journal_id.id,
            'partner_id': partner_id.id,
            'partner_type': 'customer',
            'date': fields.Date.today(),
            'payment_method_id': payment_method_line_id and payment_method_line_id[0].payment_method_id.id or False,
            'payment_method_line_id': payment_method_line_id and payment_method_line_id.id or False,
            'payment_reference': reference,
            'payment_token_id': payment_token_id,
            'payment_transaction_id': payment_transaction_id.id,
            'payment_type': 'inbound',
            'state': 'draft'
        })

    def action_send_receipt(self, payment_id):
        template = self.env.ref('account.mail_template_data_payment_receipt', raise_if_not_found=False)
        if template:
            template.sudo().with_context(lang=payment_id.partner_id.lang).send_mail(payment_id.id, force_send=True)

    def process_token_payment(self, partner_id, amount, reference, payment_token_id, provider_id, company_id, currency_id, send_receipt):
        payment_provider_id = self.env['payment.provider'].browse(provider_id)
        if hasattr(self.env['stride.invoice.payment'], '%s_process_token_payment' % payment_provider_id.code):
            getattr(self.env['stride.invoice.payment'], '%s_process_token_payment' % payment_provider_id.code)(partner_id=partner_id, amount=amount, reference=reference, payment_token_id=payment_token_id, provider_id=provider_id, company_id=company_id, currency_id=currency_id, send_receipt=send_receipt)

    def process_card_payment(self, response, partner_id, amount, reference, provider_id, company_id, currency_id, send_receipt, capture_token):
        payment_provider_id = self.env['payment.provider'].browse(provider_id)
        if hasattr(self.env['stride.invoice.payment'], '%s_process_card_payment' % payment_provider_id.code):
            getattr(self.env['stride.invoice.payment'], '%s_process_card_payment' % payment_provider_id.code)(response=response, partner_id=partner_id, amount=amount, reference=reference, provider_id=provider_id, company_id=company_id, currency_id=currency_id, send_receipt=send_receipt, capture_token=capture_token)