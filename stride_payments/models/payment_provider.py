from odoo import _, api, fields, models

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    import_transactions_batch = fields.Boolean(string='Import Transactions Batch')

    @api.model
    def update_invoice_payment_method_type(self):
        usio = self.env['ir.module.module'].sudo().search([('name', '=', 'stride_payments_usio')], limit=1)
        payengine = self.env['ir.module.module'].sudo().search([('name', '=', 'stride_payments_pe')], limit=1)
        if usio and usio.state == 'installed':
            payengine_provider = self.env['payment.provider'].search([('code', '=', 'payengine')])
            if payengine_provider:
                payengine_provider.write({'stride_payment_method_type': False})

        if payengine and payengine.state == 'installed':
            usio_provider = self.env['payment.provider'].search([('code', '=', 'stride')])
            if usio_provider:
                usio_provider.write({'payengine_payment_method_type': False})

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        context = self.env.context
        usio = self.env['ir.module.module'].sudo().search([('name', '=', 'stride_payments_usio')], limit=1)
        payengine = self.env['ir.module.module'].sudo().search([('name', '=', 'stride_payments_pe')], limit=1)
        domain = False
        if context.get('payment_method') and context.get('payment_method') == 'card':
            if usio and usio.state == 'installed':
                domain = [('stride_payment_method_type', '=', 'credit_card')]
            if payengine and payengine.state == 'installed':
                domain = [('payengine_payment_method_type', '=', 'credit_card')]
            if usio and usio.state == 'installed' and payengine and payengine.state == 'installed':
                domain = ['|', ('stride_payment_method_type', '=', 'credit_card'), ('payengine_payment_method_type', '=', 'credit_card')]
        if context.get('payment_method') and context.get('payment_method') == 'bank':
            if usio and usio.state == 'installed':
                domain = [('stride_payment_method_type', '=', 'bank_account')]
            if payengine and payengine.state == 'installed':
                domain = [('payengine_payment_method_type', '=', 'bank_account')]
            if usio and usio.state == 'installed' and payengine and payengine.state == 'installed':
                domain = ['|', ('stride_payment_method_type', '=', 'bank_account'), ('payengine_payment_method_type', '=', 'bank_account')]
        if domain:
            args += domain
        return super(PaymentProvider, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)