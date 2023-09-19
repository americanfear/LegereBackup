import logging

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def legere_create_invoices(self):
        self.ensure_one()
        if self.advance_payment_method == 'delivered':
            invoice = self.sale_order_ids._create_invoices(final=self.deduct_down_payments)
            return invoice.id

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def legere_create_payments(self):
        self.ensure_one()
        payment = self._create_payments()
        return payment.id

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create_base_automation_auto_create_sale_invoice(self):
        base_automation_pool = self.env['base.automation']
        auto_create_sale_invoice = base_automation_pool.search([('name', '=', 'Sale Auto Create Invoice')], limit=1)
        if not auto_create_sale_invoice:
            delivery_status_field = self.env['ir.model.fields'].search([('name', '=', 'delivery_status'),
                ('model', '=', 'sale.order')], limit=1)
            base_automation_pool.create({
                "name": "Sale Auto Create Invoice",
                "trigger": "on_write",
                "state": 'code',
                "model_id": self.env.ref("sale.model_sale_order").id,
                "type": "ir.actions.server",
                "trigger_field_ids": [(6, 0, [delivery_status_field.id])],
                "code": "records.auto_create_sale_invoice()",
            })
        return

    def auto_create_sale_invoice(self):
        for record in self:
            try:
                if record.delivery_status == 'full':
                    if record.state in ['draft', 'sent']:
                        record.action_confirm()
                    if record.invoice_status == 'to invoice':
                        sale_advance_payment = self.env['sale.advance.payment.inv'].sudo().create({
                            'advance_payment_method': 'delivered',
                            'sale_order_ids': [(6,0, [record.id])],
                            'deduct_down_payments': True
                        })
                        invoice = sale_advance_payment._create_invoices(record)
                        invoice.action_post()

                        template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
                        if template and invoice.partner_id.email and invoice.invoice_payment_term_id and invoice.amount_residual != 0.0:
                            template.with_context({'mark_invoice_as_sent': True}).send_mail(invoice.id, force_send=True)

                        if template and invoice.partner_id.email and not invoice.invoice_payment_term_id and invoice.amount_residual == 0.0:
                            template.with_context({'mark_invoice_as_sent': True}).send_mail(invoice.id, force_send=True)
                        
                        if not invoice.invoice_payment_term_id and invoice.amount_residual > 0.0:
                            self.env['mail.activity'].create({
                                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                'date_deadline': fields.Date.today() + relativedelta(days=1),
                                'res_id': invoice.id,
                                'user_id': invoice.invoice_user_id.id,
                                'res_model_id': self.env['ir.model']._get_id('account.move'),
                                'summary': 'Issue with auto invoice creation',
                            })
            except Exception as e:
                _logger.error("%s", str(e))

    @api.onchange('partner_id')
    def onchange_partner(self):
        self.license_partner_id = False

    @api.depends('order_line', 'order_line.product_id')
    def _compute_license_required(self):
        for record in self:
            record.license_required = True if record.order_line.filtered(lambda x: x.product_id and x.product_id.license_required) else False

    @api.onchange('license_partner_id', 'license_partner_id.license_expiration_date')
    def _compute_license_expired(self):
        for record in self:
            record.license_expired = True if record.license_partner_id and record.license_partner_id.license_expiration_date and record.license_partner_id.license_expiration_date < fields.Date.today() else False

    @api.depends('partner_id')
    def _compute_customer_current_limit(self):
        for record in self:
            record.customer_current_limit = record.partner_id.credit

    license_partner_id = fields.Many2one('res.partner', string='License Partner', domain="[('id', 'child_of', partner_id), ('licensed', '!=', False)]")
    license_required = fields.Boolean(string='License Required', compute='_compute_license_required', store=True)
    license_expired = fields.Boolean(string='License Expired', compute='_compute_license_expired')
    customer_current_limit = fields.Monetary(string='Customer Current Limit', compute='_compute_customer_current_limit')
    allowed_change_unit_price = fields.Boolean(compute='_compute_allowed_change_unit_price')
    price_change_approved = fields.Boolean(string='Price Change Approved')

    @api.depends('price_change_approved')
    def _compute_allowed_change_unit_price(self):
        for record in self:
            record.allowed_change_unit_price = True #if record.price_change_approved or self.env.user.has_group('sales_team.group_sale_manager') else False

    def action_approve_price_change(self):
        for record in self:
            record.write({'price_change_approved': True})

    def action_confirm_check(self):
        for record in self:
            if record.license_partner_id and record.license_expired and not self.env.context.get('skip_license_expired_check'):
                return record.raise_warning(warning_type='license_expired')
            record.action_confirm()                        
             
    
    def raise_warning(self, warning_type=None):
        view = self.env.ref('legere_sales.view_sale_order_check_confirm_fingerprint_wizard')
        wiz = self.env['sale.order.check.confirm.wizard'].create({'sale_order_id': self.id,
            'warning_type': warning_type})
        return {
            'name': _('Check Warning'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.check.confirm.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context': self.env.context,
        }

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    dummy_price_unit = fields.Float(string="Unit Price", related='price_unit', readonly=True)
