# -*- coding: utf-8 -*-

from odoo import http
import json
from odoo.http import request
from datetime import datetime, timezone
from werkzeug.exceptions import Forbidden, NotFound

class EasypostTracking(http.Controller):

    @http.route('/webhook/easypost', csrf=False, type='json', methods=['POST'],auth='public')
    def easypost_tracking(self, **kw):
        req = json.loads(request.httprequest.data)      
        event = req['description']
        if event in ['tracker.created','tracker.updated']:           
            result = req['result']
            shipment_id = result['shipment_id']
            est_delivery_date = result['est_delivery_date']
            tracking_details = result['tracking_details'][-1]
            status = tracking_details['status']
            tracking_location = tracking_details['tracking_location']
            city = tracking_location['city'] or ''
            state = tracking_location['state'] or ''
            country = tracking_location['country'] or ''
            zip = tracking_location['zip'] or ''
            d = datetime.fromisoformat(tracking_details['datetime'][:-1]).astimezone(timezone.utc)
            tracking_time = d.strftime('%Y-%m-%d %H:%M:%S')
            
            est_delivery_date = datetime.fromisoformat(est_delivery_date[:-1]).astimezone(timezone.utc)
            est_delivery_date = est_delivery_date.strftime('%Y-%m-%d %H:%M:%S')
            
            shipment = request.env['easypost.shipment'].sudo().search([('shipping_id','=',shipment_id)],limit=1)
            if shipment:
                shipment.write({'tracking_status': status, 'est_delivery_date': est_delivery_date})
                request.env['easypost.shipment.tracking'].sudo().create({
                    'shipment':shipment.id,
                    'tracking_city':city,
                    'tracking_state':state,
                    'tracking_country':country,
                    'tracking_zip':zip,
                    'tracking_time':tracking_time,
                    'tracking_status':status,
                    'name': tracking_details.get('message', "")
                    })
        return True

    @http.route(['/tracking/<string:shipment_ID>'], type='http', auth="public", website=True)
    def easypost_shipment_tracking(self, shipment_ID, **kw):
        if not shipment_ID:
            raise NotFound()
        shipment = request.env['easypost.shipment'].sudo().search([('shipping_id', '=', shipment_ID)], limit=1)
        if not shipment:
            raise NotFound()

        tracking_ids = request.env['easypost.shipment.tracking'].sudo().search([('shipment', '=', shipment.id)], order='tracking_time desc')
        last_tracking_id = request.env['easypost.shipment.tracking'].sudo().search([('shipment', '=', shipment.id)], order='tracking_time desc', limit=1)
        values = {
            'shipment': shipment,
            'tracking_ids': tracking_ids,
            'last_tracking_id': last_tracking_id,
            'easypost_carrier_type': shipment.picking_id.carrier_id and shipment.picking_id.carrier_id.easypost_carrier_id and shipment.picking_id.carrier_id.easypost_carrier_id.easypost_carrier_type or False
        }
        return request.render('stride_delivery.easypost_shipment_tracking_template', values)
