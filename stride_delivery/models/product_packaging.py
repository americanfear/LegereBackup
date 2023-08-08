from odoo import models, fields, api

class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    custom_height = fields.Integer('Height', help="Custom Packaging Height")
    custom_width = fields.Integer('Width', help="Custom Packaging Width")
    custom_length = fields.Integer('Length', help="Custom Packaging Length")

class CarrierPredefinePackage(models.Model):
    _name = 'carrier.predefine.package'
    _description = "Carrier Predefine Package"

    name = fields.Char('Name', required=True)
    easypost_carrier_type = fields.Many2one('easypost.carrier.type', 'Easypost Carrier Type')
    
class StockPackageType(models.Model):
    _inherit = 'stock.package.type'

    package_carrier_type = fields.Selection(selection_add=[('easypost', 'Easypost')])
    predefine_package_id = fields.Many2one('carrier.predefine.package', 'Package Name')
    easypost_carrier_type = fields.Many2one('easypost.carrier.type', 'Easypost Carrier Type')
    customs_package = fields.Boolean(string='Customs Package')
    
    @api.onchange('easypost_carrier_type')
    def onchange_carrier_type(self):
        self.predefine_package_id = False
        self.shipper_package_code = False
    
    @api.onchange('predefine_package_id')
    def onchange_predefined_package(self):
        self.shipper_package_code = self.predefine_package_id.name