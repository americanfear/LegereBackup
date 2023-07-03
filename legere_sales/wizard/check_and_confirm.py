from odoo import models, fields, api, _

class SaleCheckConfirmWizard(models.TransientModel):    
    _name = 'sale.order.check.confirm.wizard'
    _description = 'Wizard to show errors during sale order check process'

    def _get_service_products(self):
        for record in self:
            record.service_products = record.sale_order_id.order_line.filtered(lambda x: x.product_id.type == 'service').mapped('product_id.name')

    sale_order_id = fields.Many2one('sale.order', 'Sale Order', required=True)
    warning_type = fields.Selection([('license_expired', 'License Expired')], string='Warning Type')
    
    def action_force_confirm(self):
        if self.warning_type == 'license_expired':
            return self.sale_order_id.with_context({'skip_license_expired_check': True}).action_confirm_check()
        return self.sale_order_id.action_confirm()