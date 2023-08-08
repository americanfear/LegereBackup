from odoo import api, fields, models, _

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
            record.license_expired = True if record.license_partner_id and record.license_partner_id.license_expiration_date < fields.Date.today() else False

    @api.depends('partner_id')
    def _compute_customer_current_limit(self):
        for record in self:
            record.customer_current_limit = record.partner_id.credit

    license_partner_id = fields.Many2one('res.partner', string='License Partner', domain="[('id', 'child_of', partner_id), ('licensed', '!=', False)]")
    license_required = fields.Boolean(string='License Required', compute='_compute_license_required', store=True)
    license_expired = fields.Boolean(string='License Expired', compute='_compute_license_expired')
    customer_current_limit = fields.Monetary(string='Customer Current Limit', compute='_compute_customer_current_limit')

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
