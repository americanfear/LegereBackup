from odoo import api, fields, models, _

class ProductCategory(models.Model):
    _inherit = "product.category"

    olympia_product = fields.Boolean(string='Olympia Product Category')

class ProductTemplate(models.Model):
    _inherit = "product.template"

    license_required = fields.Boolean(string='License Required')