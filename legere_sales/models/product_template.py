from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = "product.template"

    license_required = fields.Boolean(string='License Required')