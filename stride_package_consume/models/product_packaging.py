from odoo import models, fields, api

class StockPackageType(models.Model):
    _inherit = 'stock.package.type'

    default_location_src_id = fields.Many2one('stock.location', 'Product Consume Source Location')
    default_location_dest_id = fields.Many2one('stock.location', 'Product Consume Destination Location')
    product_packaging_consume_ids = fields.One2many('product.packaging.consume', 'stock_package_type_id', string='Product Packaging Consume')

class ProductPackagingConsume(models.Model):
    _name = 'product.packaging.consume'
    _description = 'Product Packaging Consume'

    product_id = fields.Many2one('product.product', 'Product', required=True,  domain="[('type', '!=', 'service'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id', store=True)
    quantity = fields.Float(
        'Quantity', default=0.0, digits='Product Unit of Measure', required=True, copy=False)
    stock_package_type_id = fields.Many2one('stock.package.type', string='Packaging Type', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
        default=lambda self: self.env.company)
