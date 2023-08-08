from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    bill_third_party_carrier = fields.Many2one('easypost.carrier', string="Shipping Carrier")
    bill_third_party_account = fields.Char(string="Billing Account No", help="Account # for billing provider")
    bill_third_party_zip = fields.Char(string="Billing Account ZIP")