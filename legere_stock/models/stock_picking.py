from odoo import api, fields, models, _

class Menu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def update_replenishment_menu_group(self):
        menu_replenish = self.env['ir.model.data']._xmlid_to_res_id('stock.menu_reordering_rules_replenish')
        stock_group_user = self.env['ir.model.data']._xmlid_to_res_id('stock.group_stock_user')
        if menu_replenish:
            menu_replenish = self.env['ir.ui.menu'].browse(menu_replenish)
            menu_replenish.write({'groups_id': [(6, 0, [stock_group_user])]})

class StockPicking(models.Model):
    _inherit = "stock.picking"

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