from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"

    order_notes = fields.Text(string='Order Notes')