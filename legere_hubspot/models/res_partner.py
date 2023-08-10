from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    hubspot_id = fields.Char(string='Hubspot ID')