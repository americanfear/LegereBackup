from odoo import api, fields, models

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    authorize_account_type = fields.Char(string='Authorize Account Type')