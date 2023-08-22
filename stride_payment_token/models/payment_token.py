from odoo import api, fields, models

class PaymentToken(models.Model):
    _inherit = 'payment.token'

    expiration_date = fields.Date(string='Expiration Date')
