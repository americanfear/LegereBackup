from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    shipping_items = fields.Text(string="Shipping Items")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    shipping_items = fields.Text(string="Shipping Items", related='company_id.shipping_items', readonly=False, store=True)