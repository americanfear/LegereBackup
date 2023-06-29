from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    licensed = fields.Boolean(string='Is Licensed')
    license_number = fields.Char(string='License Number')
    license_expiration_date = fields.Date(string='License Expiration Date')