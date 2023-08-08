from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_download_shipping_label = fields.Boolean(string='Auto download shipping labels', default=False)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_download_shipping_label = fields.Boolean(string='Auto download shipping labels', related='company_id.auto_download_shipping_label', store=True, readonly=False)