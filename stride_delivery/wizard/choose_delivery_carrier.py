from odoo import fields, models, api, _

class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    no_of_packages = fields.Integer('Estimate Number of Packages', default=0)
    
    def _get_shipment_rate(self):
        result = super(ChooseDeliveryCarrier, self)._get_shipment_rate()
        if self.carrier_id.delivery_type == 'easypost':
            vals = self.carrier_id.rate_shipment(self.order_id)
            if vals.get('success'):
                self.no_of_packages = vals['no_of_packages']
        return result