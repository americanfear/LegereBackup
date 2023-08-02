from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_custom = fields.Boolean(
        string="Is Custom Product",
        help="Mark if this product needs to use the custom services flow",
    )
    group_task = fields.Boolean(string='Group Task Per Order')
    custom_project_id = fields.Many2one('project.project', string="Project for Custom Services")