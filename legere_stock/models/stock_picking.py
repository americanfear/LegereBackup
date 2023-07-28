from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.depends('sale_id')
    def _compute_delivery_picking(self):
        for record in self:
            if record.picking_type_id.warehouse_id.pick_type_id == record.picking_type_id and record.sale_id:
                outgoing_picking = record.sale_id.picking_ids.filtered(lambda x: x.picking_type_id.code == 'outgoing' and x.state != 'cancel')
                if outgoing_picking:
                    record.delivery_picking = outgoing_picking[0].name
                else:
                    record.delivery_picking = ''
            else:
                record.delivery_picking = ''        

    delivery_picking = fields.Char(string='Delivery Picking', compute='_compute_delivery_picking')