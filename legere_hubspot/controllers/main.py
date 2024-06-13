import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class Hubspot(http.Controller):

    @http.route('/webhook/hubspot', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def hubspot_data(self, **kwargs):
        contact_pool = request.env['res.partner'].sudo()
        state_pool = request.env['res.country.state'].sudo()
        country_pool = request.env['res.country'].sudo()
        hubspot_log_pool = request.env['hubspot.log'].sudo()
        _logger.info("=======Hubspot Data======= %s", json.loads(request.httprequest.data.decode('utf-8')))
        for data in json.loads(request.httprequest.data.decode('utf-8')):
            try:
                updated = False
                if data.get('subscriptionType') == 'contact.creation' and data.get('objectId'):
                    contact = contact_pool.search([('hubspot_id', '=', data.get('objectId'))], limit=1)
                    if not contact:
                        contact = contact_pool.create({
                            'name': 'HubspotContact',
                            'hubspot_id': data.get('objectId')
                        })
                        request.cr.commit()
                        updated = True  
                
                if data.get('subscriptionType') == 'contact.propertyChange' and data.get('objectId'):
                    contact = contact_pool.search([('hubspot_id', '=', data.get('objectId'))], limit=1)
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
                    hubspot_log_pool.create({
                        'data': data,
                        'is_updated': True,
                        'record_id': contact.id,
                    })
                elif not updated and data.get('propertyName') in ['firstname', 'lastname', 'email', 'phone', 'jobtitle', 'mobilephone', 'website', 'address', 'zip', 'city', 'state_dd', 'country']:
                    hubspot_log_pool.create({
                        'data': data,
                        'is_updated': False
                    })
            except Exception as e:
                hubspot_log_pool.create({
                    'data': data,
                    'error': str(e),
                })
        hubspot_log_pool.search([('is_updated', '=', False)]).update_contact()
        return "Received HubSpot data successfully"