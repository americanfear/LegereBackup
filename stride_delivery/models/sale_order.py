from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_order_tracking_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        access_url = base_url + '/my/orders/' + str(self.id)
        if self.access_token:
            access_url += '?access_token=' + self.access_token
        return access_url