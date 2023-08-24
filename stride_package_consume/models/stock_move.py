from odoo import api, fields, models, tools, _
from datetime import datetime

class StockMove(models.Model):
    _inherit = "stock.move"

    def write(self, vals):
        res = super(StockMove, self).write(vals)
        if vals.get('state') == 'done':
            for record in self:
                move_line = self.env['stock.move.line'].search([('move_id', '=', record.id)])
                if move_line:
                    move_line.create_package_material_transfer()
        return res

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    package_material_transfer_created = fields.Boolean(string='Package Material Transfer Created')

    def create_package_material_transfer(self):
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'internal'), ('company_id', '=', self.env.company.id)], limit=1)
        for record in self.filtered(lambda x: x.result_package_id and x.result_package_id.package_type_id and x.result_package_id.package_type_id.product_packaging_consume_ids and x.picking_id.picking_type_id.packaging_consume_step):
            package_material_transfer_created_move = self.env['stock.move.line'].search([('picking_id', '=', record.picking_id.id), ('result_package_id', '=', record.result_package_id.id), ('package_material_transfer_created', '=', True)])
            if not package_material_transfer_created_move:
                picking_id = False
                for packaging_consume in record.result_package_id.package_type_id.product_packaging_consume_ids:
                    customerloc = self.env['stock.location'].search(['|', '&', ('company_id', '=', self.env.company.id), ('company_id', '=', False), ('usage', '=', 'customer')], limit=1)
                    location_id = (record.result_package_id.package_type_id.default_location_src_id and record.result_package_id.package_type_id.default_location_src_id.id) or (record.move_id.warehouse_id.lot_stock_id.id)
                    location_dest_id = (record.result_package_id.package_type_id.default_location_dest_id and record.result_package_id.package_type_id.default_location_dest_id.id) or customerloc.id

                    if not picking_id:
                        picking_id = self.env['stock.picking'].create({
                            'origin': record.move_id.origin or record.move_id.name,
                            'company_id': record.company_id.id,
                            'user_id': False,
                            'move_type': 'one',
                            'partner_id': False,
                            'picking_type_id': picking_type_id and picking_type_id.id or False,
                            'location_id': location_id,
                            'location_dest_id': location_dest_id,
                        })
                    
                    move = self.env['stock.move'].create({
                        'date': fields.Datetime.now(),
                        'picking_id': picking_id.id,
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'name': record.move_id.origin or record.move_id.name,
                        'procure_method': 'make_to_stock',
                        'product_id': packaging_consume.product_id.id,
                        'product_uom': packaging_consume.product_uom_id.id,
                        'product_uom_qty': packaging_consume.quantity,
                        'partner_id': False,
                        'picking_type_id': picking_type_id and picking_type_id.id or False,
                        })
                try:                    
                    picking_id.action_confirm()
                    picking_id.action_assign()
                    if picking_id.state != 'assigned':
                        raise
                    for move in picking_id.move_ids.filtered(lambda m: m.state not in ['done', 'cancel']):
                        for move_line in move.move_line_ids:
                            move_line.qty_done = move_line.reserved_uom_qty
                    picking_id.button_validate()
                except:
                    self.env['mail.activity'].create({
                        "activity_type_id": 6, #exception
                        "summary": "There Was an error auto confimring packaging consumption",
                        "note": 'This transfer could not be automatically confirmed. Please find error and validate transfer to consume package items',
                        "res_id": picking_id.id,
                        "user_id": picking_id.create_uid.id,
                        'res_model_id': self.env['ir.model']._get_id('stock.picking'),
                        "date_deadline": datetime.strftime(datetime.now(), "%Y-%m-%d")
                    })
                    
            record.package_material_transfer_created = True