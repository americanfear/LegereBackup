from odoo import fields, models, api, _
from odoo.tools.float_utils import float_compare

class ChooseDeliveryPackage(models.TransientModel):
    _inherit = 'choose.delivery.package'

    height = fields.Integer('Height', help="Packaging Height")
    width = fields.Integer('Width', help="Packaging Width")
    packaging_length = fields.Integer('Length', help="Packaging Length")
    customs_package = fields.Boolean(string='Customs Package')

    def action_put_in_pack(self):
        picking_move_lines = self.picking_id.move_line_ids
        if not self.picking_id.picking_type_id.show_reserved and not self.env.context.get('barcode_view'):
            picking_move_lines = self.picking_id.move_line_nosuggest_ids

        move_line_ids = picking_move_lines.filtered(lambda ml:
            float_compare(ml.qty_done, 0.0, precision_rounding=ml.product_uom_id.rounding) > 0
            and not ml.result_package_id
        )
        if not move_line_ids:
            move_line_ids = picking_move_lines.filtered(lambda ml: float_compare(ml.reserved_uom_qty, 0.0,
                                 precision_rounding=ml.product_uom_id.rounding) > 0 and float_compare(ml.qty_done, 0.0,
                                 precision_rounding=ml.product_uom_id.rounding) == 0)

        delivery_package = self.picking_id._put_in_pack(move_line_ids)
        # write shipping weight and package type on 'stock_quant_package' if needed
        if self.delivery_package_type_id:
            delivery_package.package_type_id = self.delivery_package_type_id
        if self.shipping_weight:
            delivery_package.shipping_weight = self.shipping_weight
        if self.customs_package:
            delivery_package.custom_height = self.height
            delivery_package.custom_width = self.width
            delivery_package.custom_length = self.packaging_length

    @api.onchange('delivery_package_type_id')
    def _onchange_delivery_package_type(self):
        self.customs_package = False
        self.height = 0
        self.width = 0
        self.packaging_length = 0
        if self.delivery_package_type_id:
            self.customs_package = self.delivery_package_type_id.customs_package
            self.height = self.delivery_package_type_id.height
            self.width = self.delivery_package_type_id.width
            self.packaging_length = self.delivery_package_type_id.packaging_length