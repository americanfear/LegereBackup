from odoo import api, fields, models, _

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

    license_partner_id = fields.Many2one('res.partner', string='License Partner', domain="[('id', 'child_of', partner_id), ('licensed', '!=', False)]")
    license_required = fields.Boolean(string='License Required', compute='_compute_license_required', store=True)
    license_expired = fields.Boolean(string='License Expired', compute='_compute_license_expired')