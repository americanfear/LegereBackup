
from odoo import api, fields, models, _

class HubspotLog(models.Model):
    _name = 'hubspot.log'
    _description = 'Hubspot Log'
    _rec_name = 'record_id'

    data = fields.Text(string='Data', required=True)
    error = fields.Text(string='Error')
    is_updated = fields.Boolean(string='Updated')
    record_id = fields.Many2one('res.partner', string='Record', required=False)


# class HubspotAccount(models.Model):
#     _name = 'hubspot.account'
#     _description = 'Hubspot Account'

#     name = fields.Char('Name', required=True)
#     url = fields.Char('Url', required=True)
#     consumer_key = fields.Char(string='Consumer Key', required=False)
#     consumer_secret = fields.Char(string='Consumer Secret', required=False)
#     active = fields.Boolean(string='Active', default=True)
#     company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)