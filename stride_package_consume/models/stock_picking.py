from odoo import api, fields, models, tools, _

class PickingType(models.Model):
    _inherit = "stock.picking.type"

    packaging_consume_step = fields.Boolean(string='Packaging Consume Step')