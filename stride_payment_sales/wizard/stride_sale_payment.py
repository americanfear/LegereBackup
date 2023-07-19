import logging
from odoo import _, api, fields, models,_
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class StrideSalePayment(models.Model):
    _name = 'stride.sale.payment'
    _description = 'Stride Sale Payment'

    @api.depends('sale_order_id')
    def _get_reference(self):
        for record in self:
            record.reference = record.sale_order_id.name

    @api.depends('sale_order_id', 'company_id')
    def _get_email(self):
        for record in self:
            email = record.sale_order_id.partner_invoice_id.email or record.sale_order_id.partner_id.email or record.company_id.partner_id.email or 'info@yourcompany.com'
            record.email =  email

    def _get_default_provider(self):
        return self.env['payment.provider'].search([('state', '!=', 'disabled')], limit=1)

    partner_id = fields.Many2one('res.partner', string='Partner', related='sale_order_id.partner_invoice_id')
    amount = fields.Monetary(string='Amount', compute=False, required=True)
    reference = fields.Char(string='Reference', compute='_get_reference')
    payment_method = fields.Selection([('card', 'Credit Card'),
        ('bank', 'Bank Account'),
        ('token', 'Token')], default='card', string='Payment Method', required=True)
    payment_token_id = fields.Many2one('payment.token', string='Saved payment token',
        domain="[('provider_id', '=', provider_id), ('partner_id', '=', partner_id)]")
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    provider_id = fields.Many2one('payment.provider', string='Payment Provider', required=True,
        default=_get_default_provider,
        domain="[('state', '!=', 'disabled')]")
    provider_code = fields.Selection(related='provider_id.code', store=True)
    provider_state = fields.Selection(related='provider_id.state', store=True)
    email = fields.Char(string='Email', compute='_get_email')
    partner_email = fields.Char(string='Partner Email', related='partner_id.email')
    send_receipt = fields.Boolean(string='Send Payment Receipt', default=False)
    order_confirm = fields.Boolean(string='Auto Confirm Sale Order', default=False)
    create_downpayment = fields.Boolean(string='Create Down Payment Invoice', default=False)
    auto_invoice = fields.Boolean(string='Create Final Invoice', default=False)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)

    @api.onchange('auto_invoice')
    def onchange_auto_invoice(self):
        if self.auto_invoice:
            self.order_confirm = True
            self.create_downpayment = False
            self.amount = self.sale_order_id.amount_payment_due

    @api.onchange('create_downpayment')
    def onchange_create_downpayment(self):
        if self.create_downpayment:
            self.order_confirm = True
            self.auto_invoice = False

    @api.onchange('order_confirm')
    def onchange_order_confirm(self):
        if not self.order_confirm:
            self.create_downpayment = False
            self.auto_invoice = False

    def action_register_sale_payment(self):
        return True

    def action_send_receipt(self, payment_id):
        template = self.env.ref('account.mail_template_data_payment_receipt', raise_if_not_found=False)
        if template:
            template.sudo().with_context(lang=payment_id.partner_id.lang).send_mail(payment_id.id, force_send=True)

    def pre_processing(self, order_id, order_confirm, create_downpayment, auto_invoice, amount):
        sale_order = self.env['sale.order'].browse(order_id)
        if order_confirm and sale_order.state in ['draft', 'sent']:
            sale_order.action_confirm()
        if create_downpayment and sale_order.state in ['sale']:
            sale_advance_payment = self.env['sale.advance.payment.inv'].create({
                'advance_payment_method': 'fixed',
                'sale_order_ids': [(6,0, [sale_order.id])],
                'fixed_amount': amount
            })
            return sale_advance_payment._create_invoices(sale_order)
        if auto_invoice and sale_order.state in ['sale']:
            sale_advance_payment = self.env['sale.advance.payment.inv'].create({
                'advance_payment_method': 'delivered',
                'sale_order_ids': [(6,0, [sale_order.id])],
                'deduct_down_payments': True
            })
            return sale_advance_payment._create_invoices(sale_order)
        return False

    def process_token_payment(self, order_id, partner_id, amount, reference, payment_token_id, provider_id, company_id, currency_id, send_receipt, order_confirm, create_downpayment, auto_invoice):
        invoice = self.env['stride.sale.payment'].pre_processing(order_id=order_id, order_confirm=order_confirm, create_downpayment=create_downpayment, auto_invoice=auto_invoice, amount=amount)
        if invoice:
            invoice.action_post()
        payment_provider_id = self.env['payment.provider'].browse(provider_id)
        if hasattr(self.env['stride.sale.payment'], '%s_process_token_payment' % payment_provider_id.code):
            getattr(self.env['stride.sale.payment'], '%s_process_token_payment' % payment_provider_id.code)(order_id=order_id, partner_id=partner_id, amount=amount, reference=reference, payment_token_id=payment_token_id, provider_id=provider_id, company_id=company_id, currency_id=currency_id, send_receipt=send_receipt, invoice=invoice)

    def process_card_payment(self, response, order_id, partner_id, amount, reference, provider_id, company_id, currency_id, send_receipt, order_confirm, create_downpayment, auto_invoice):
        invoice = self.env['stride.sale.payment'].pre_processing(order_id=order_id, order_confirm=order_confirm, create_downpayment=create_downpayment, auto_invoice=auto_invoice, amount=amount)
        if invoice:
            invoice.action_post()
        payment_provider_id = self.env['payment.provider'].browse(provider_id)
        if hasattr(self.env['stride.sale.payment'], '%s_process_card_payment' % payment_provider_id.code):
            getattr(self.env['stride.sale.payment'], '%s_process_card_payment' % payment_provider_id.code)(response=response, order_id=order_id, partner_id=partner_id, amount=amount, reference=reference, provider_id=provider_id, company_id=company_id, currency_id=currency_id, send_receipt=send_receipt, invoice=invoice)
    
    def create_payment_transaction(self, order_id, partner_id, amount, reference, payment_token_id, provider_id, company_id, currency_id, invoice):
        payment_provider_id = self.env['payment.provider'].browse(provider_id)
        partner_id = self.env['res.partner'].browse(partner_id)
        sale_order = self.env['sale.order'].browse(order_id)
        reference = self.env['payment.transaction']._compute_reference(
            payment_provider_id.code,
            prefix=reference
        )

        return self.env['payment.transaction'].create({
            'provider_id': payment_provider_id.id,
            'amount': amount,
            'company_id': company_id,
            'currency_id': currency_id,
            'invoice_ids': [(6, 0, invoice and [invoice.id] or [])],
            'sale_order_ids': [(6, 0, [sale_order.id])],
            'partner_id': partner_id.id,
            'token_id': payment_token_id,
            'reference': reference,
            'operation': 'online_direct',
        })

    def create_account_payment(self, partner_id, amount, reference, payment_token_id, provider_id, company_id, currency_id, payment_transaction_id):
        payment_provider_id = self.env['payment.provider'].browse(provider_id)
        partner_id = self.env['res.partner'].browse(partner_id)

        payment_method_line_id = payment_provider_id.journal_id.inbound_payment_method_line_ids.filtered(lambda x: x.payment_method_id.name == 'Authorize.Net')
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