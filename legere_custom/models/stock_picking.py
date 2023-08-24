from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    order_notes = fields.Text(string='Order Notes', related='sale_id.order_notes')