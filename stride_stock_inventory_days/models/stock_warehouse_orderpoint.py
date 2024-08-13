import logging
from odoo import SUPERUSER_ID, _, api, fields, models, registry
from odoo.tools import float_compare

class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    use_days_of_inventory = fields.Boolean(string='Use days of inventory')


    @api.depends('qty_multiple', 'qty_forecast', 'product_min_qty', 'product_max_qty', 'visibility_days')
    def _compute_qty_to_order(self):
        super()._compute_qty_to_order()
        for orderpoint in self:
            rounding = orderpoint.product_uom.rounding
            if orderpoint.use_days_of_inventory and orderpoint.product_min_qty and orderpoint.product_max_qty:
                orderpoint.qty_to_order = False
                if orderpoint.product_id.days_of_inventory < orderpoint.product_min_qty:
                    if float_compare(orderpoint.product_max_qty - orderpoint.product_min_qty, 0.0, precision_rounding=rounding) > 0:
                        orderpoint.qty_to_order = orderpoint.product_id.average_sold * (orderpoint.product_max_qty - orderpoint.product_min_qty)
