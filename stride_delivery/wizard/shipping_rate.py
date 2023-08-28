from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError

class EasypostShippingRate(models.Model):
    _name = 'easypost.shipping.rate'
    _description = "Shipping Rate"


    stock_picking_id = fields.Many2one('stock.picking', string='Stock Picking')
    line_ids = fields.One2many('easypost.shipping.rate.line', 'easypost_shipping_rate_id', string='Lines')

    def do_action(self):
        for record in self:
            if record.stock_picking_id:
                selected_line = record.line_ids.filtered(lambda x: x.is_selected)
                if len(selected_line) != 1:
                    raise ValidationError("Please select one service.")

                carrier_id = self.env['delivery.carrier'].search([('delivery_type', '=', 'easypost'),
                                ('easypost_carrier_id.easypost_carrier_type', '=', selected_line[0].carrier),
                                ('service_level.name', '=', selected_line[0].service)], limit=1)
                if carrier_id:
                    record.stock_picking_id.carrier_id = carrier_id.id
                    record.stock_picking_id.add_insurance = carrier_id.add_insurance
                    record.stock_picking_id.add_sat_delivery = carrier_id.add_sat_delivery
                    record.stock_picking_id.add_signature = carrier_id.add_signature
                    record.stock_picking_id.eel_pfc = carrier_id.eel_pfc
                    record.stock_picking_id.create_return_label = carrier_id.create_return_label
                    record.stock_picking_id.packaging_id = carrier_id.packaging_id.id

class EasypostShippingRateLine(models.Model):
    _name = 'easypost.shipping.rate.line'
    _description = "Shipping Rate Line"
    _order = 'rate'

    easypost_shipping_rate_id = fields.Many2one('easypost.shipping.rate', string='Easypost Shipping Rate', ondelete='cascade')
    carrier = fields.Char(string='Carrier', readonly=True)
    service = fields.Char(string='Service', readonly=True)
    rate = fields.Float(string='Rate', readonly=True)
    is_selected = fields.Boolean(string='Selected')
    est_delivery_days = fields.Integer(string='Estimated Delivery Days')