import ast

from odoo import api, fields, models, _

class HubspotLog(models.Model):
    _name = 'hubspot.log'
    _description = 'Hubspot Log'
    _rec_name = 'record_id'

    def _auto_delete_hubspot_log(self):
        today = fields.Datetime.now()
        for record in self.search([('id', '!=', False)]):
            delta = today - record.create_date
            if delta.days >= 30:
                record.unlink()

    data = fields.Text(string='Data', required=True)
    error = fields.Text(string='Error')
    is_updated = fields.Boolean(string='Created/Updated')
    record_id = fields.Many2one('res.partner', string='Record', required=False)

    def update_contact(self):
        contact_pool = self.env['res.partner'].sudo()
        state_pool = self.env['res.country.state'].sudo()
        country_pool = self.env['res.country'].sudo()
        for record in self:
            try:
                data = ast.literal_eval(record.data)
                contact = contact_pool.search([('hubspot_id', '=', data.get('objectId'))], limit=1)
                updated = False
                if contact:
                    if data.get('propertyName') == 'firstname':
                        name_parts = contact.name.split()
                        if len(name_parts) >= 2:
                            contact_name =  data.get('propertyValue') + ' ' + name_parts[1]
                        else:
                            contact_name =  data.get('propertyValue')
                        contact.write({'name': contact_name})
                        updated = True
                    elif data.get('propertyName') == 'lastname':
                        name_parts = contact.name.split()
                        contact_name = name_parts[0] + ' ' + data.get('propertyValue')
                        contact.write({'name': contact_name})
                        updated = True
                    elif data.get('propertyName') == 'email':
                        contact.write({'email': data.get('propertyValue')})
                        updated = True
                    elif data.get('propertyName') == 'phone':
                        contact.write({'phone': data.get('propertyValue')})
                        updated = True
                    elif data.get('propertyName') == 'jobtitle':
                        contact.write({'function': data.get('propertyValue')})
                        updated = True
                    elif data.get('propertyName') == 'mobilephone':
                        contact.write({'mobile': data.get('propertyValue')})
                        updated = True
                    elif data.get('propertyName') == 'website':
                        contact.write({'website': data.get('propertyValue')})
                        updated = True
                    elif data.get('propertyName') == 'address':
                        contact.write({'street': data.get('propertyValue')})
                        updated = True
                    elif data.get('propertyName') == 'zip':
                        contact.write({'zip': data.get('propertyValue')})
                        updated = True
                    elif data.get('propertyName') == 'city':
                        contact.write({'city': data.get('propertyValue')})
                        updated = True
                    elif data.get('propertyName') == 'state_dd':
                        state_id = state_pool.search([('name', '=', data.get('propertyValue'))], limit=1)
                        if state_id:
                            contact.write({'state_id': state_id.id})
                            updated = True
                    elif data.get('propertyName') == 'country':
                        country_id = country_pool.search(['|', ('name', '=', data.get('propertyValue')),('code', '=', data.get('propertyValue'))], limit=1)
                        if country_id:
                            contact.write({'country_id': country_id.id})
                            updated = True
                    if updated:
                        record.sudo().write({'is_updated': True, 'record_id': contact.id})
            except Exception as e:
                record.sudo().write({
                    'error': str(e),
                })


# class HubspotAccount(models.Model):
#     _name = 'hubspot.account'
#     _description = 'Hubspot Account'

#     name = fields.Char('Name', required=True)
#     url = fields.Char('Url', required=True)
#     consumer_key = fields.Char(string='Consumer Key', required=False)
#     consumer_secret = fields.Char(string='Consumer Secret', required=False)
#     active = fields.Boolean(string='Active', default=True)
#     company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)