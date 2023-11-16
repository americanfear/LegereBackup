import easypost
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class EasypostCarrierType(models.Model):
    _name = 'easypost.carrier.type'
    _description = 'Easypost Carrier Type'
    
    name = fields.Char('Name')    
    carrier_type = fields.Char('Carrier Type', required=True)
    carrier_predefine_package_ids = fields.One2many('carrier.predefine.package', 'easypost_carrier_type')
    carrier_service_level_ids = fields.One2many('easypost.service.level', 'easypost_carrier_type')
    icon = fields.Image(string='Logo', max_width=300, max_height=300, groups="")

class EasypostCarrier(models.Model):
    _name = 'easypost.carrier'
    _inherits = {'easypost.carrier.type': 'easypost_carrier_type'}
    _description = 'Keeps a record of all EasyPost Carriers and their API key'

    name = fields.Char('Name', required=True)
    carrier_account_id = fields.Char('Carrier ID', required=True)
    bill_third_party_allowed = fields.Boolean('Is Third Party Billing Allowed')
    easypost_account_id = fields.Many2one('easypost.account', 'Easypost Account', required=True)
    easypost_carrier_type = fields.Many2one('easypost.carrier.type', 'Easypost Carrier Type', required=True, ondelete="restrict")
    active = fields.Boolean('active', default=True)

class EasypostServiceLevel(models.Model):
    _name = 'easypost.service.level'
    _rec_name = 'name'
    _description = 'EasyPost Carrier Services Levels, USPS, UPS, and FedEx are loaded by default. New ones can be created for other carriers if needed'

    name = fields.Char('Name', required=True)
    easypost_carrier_type = fields.Many2one('easypost.carrier.type', 'Easypost Carrier Type' , required=True, ondelete="restrict")
      
class EasyPostShipment(models.Model):
    _name = 'easypost.shipment'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'id desc'
    _description = 'EasyPost Shipments'

    name = fields.Char('Tacking Code', required=True)
    rate = fields.Float(string="Cost")
    shipping_id = fields.Char('Shipping ID')
    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    package_id = fields.Many2one('stock.quant.package', 'Package')
    label_url = fields.Char('Label URL')
    is_return_shipment = fields.Boolean(string='Return Shipment')
    refund_status = fields.Selection([
                                ('not_applicable', 'NA'), 
                                ('submitted', 'Submitted'), 
                                ('refunded', 'Refunded'), 
                                ('rejected', 'Rejected')
                                ], string='Refund Status', readonly=True)
    scan_form_status = fields.Selection([
                                ('not_applicable', 'NA'), 
                                ('done', 'Created'), 
                                ('cancel', 'Cancelled'), 
                                ], string='Scan Form Status', readonly=True)
    #Customs Form Details
    customs_form_url = fields.Char("Custom Form URL")
    submit_elec = fields.Selection([
                                ('na','NA'), 
                                ('yes', 'Yes'),
                                ('no', 'No')
                                ], string="Customs Submitted Electronically", readonly=True, default='na')
    #tracking Details
    tracking_url = fields.Char('EasyPost Tracking URL', tracking=True)
    tracking_status = fields.Char('Status', help="""Status of the package at the time of the scan event, possible values are \n"unknown", "pre_transit", "in_transit", "out_for_delivery", "delivered", \n"available_for_pickup", "return_to_sender", "failure", "cancelled" or "error\"""")
    est_delivery_date = fields.Datetime(string="Estimated Delivery Date")

    def get_tracking_url(self):
        if self.picking_id and self.picking_id.website_id and self.picking_id.website_id.domain:
            website_domain = self.picking_id.website_id.domain
            if 'https:' in website_domain or 'http:' in website_domain:
                return website_domain + '/tracking/' + self.shipping_id
            else:
                return 'https://' + website_domain + '/tracking/' + self.shipping_id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if self.shipping_id:
            return base_url + '/tracking/' + self.shipping_id
        else:
            return False

    @api.model_create_multi
    def create(self, vals_list):
        records = super(EasyPostShipment, self).create(vals_list)
        for record in records:
            if record.picking_id and not record.is_return_shipment:
                if record.picking_id.carrier_tracking_ref:
                    record.picking_id.write({'carrier_tracking_ref': record.picking_id.carrier_tracking_ref+','+record.name})
                else:
                    record.picking_id.write({'carrier_tracking_ref': record.name})
        return records

    def write(self, vals):
        result = super(EasyPostShipment, self).write(vals)
        if vals.get('tracking_status') in ['out_for_delivery', 'delivered']:
            for record in self:
                record.send_delivery_mail()
        return result

    def action_view_tracking_history(self):
        result = self.env['ir.actions.act_window']._for_xml_id('stride_delivery.action_easypost_shipments_tracking')
        result['domain'] = [('shipment', '=', self.id)]
        return result

    def send_delivery_mail(self):
        email_template_id = False
        sms_template_id = False
        if  self.tracking_status in ['out_for_delivery', 'delivered']:
            #Send Mail
            if self.tracking_status =='out_for_delivery' and self.picking_id.carrier_id.mail_our_delivery:
                email_template_id = self.env['ir.model.data']._xmlid_to_res_id('stride_delivery.email_template_shipment_out_for_delivery', raise_if_not_found=False)
            elif self.tracking_status =='delivered' and self.picking_id.carrier_id.mail_delivered:
                email_template_id = self.env['ir.model.data']._xmlid_to_res_id('stride_delivery.email_template_shipment_delivered', raise_if_not_found=False)
            if email_template_id:
                self.env['mail.template'].browse(email_template_id).send_mail(self.id, force_send=True)

            #Send SMS
            if self.tracking_status =='out_for_delivery' and self.picking_id.carrier_id.sms_our_delivery and self.picking_id.partner_id.mobile:
                sms_template_id = self.env['ir.model.data']._xmlid_to_res_id('stride_delivery.sms_template_easypost_shipment_out_for_delivery', raise_if_not_found=False)
            elif self.tracking_status =='delivered' and self.picking_id.carrier_id.sms_delivered and self.picking_id.partner_id.mobile:
                sms_template_id = self.env['ir.model.data']._xmlid_to_res_id('stride_delivery.sms_template_easypost_shipment_delivered', raise_if_not_found=False)
            if sms_template_id:
                sms_template_id = self.env['sms.template'].browse(sms_template_id)
                self._message_sms_with_template(
                    template=sms_template_id,
                    partner_ids=self.picking_id.partner_id.ids,
                    put_in_queue=True
                )
                
    def open_website_url(self):
        self.ensure_one()
        tracking_url = self.get_tracking_url()
        if not tracking_url:
            raise UserError(
                _("This shipment does not have a tracking url."))

        client_action = {'type': 'ir.actions.act_url',
                         'name': "Shipment Tracking Page",
                         'target': 'new',
                         'url': tracking_url}
        return client_action
    
    #todo: Currently this will duplicate tracking details, need to check to see if tracking details exist and add if needed.
    def request_tracking_details(self):
        for tracking in self:
            environment_key = tracking.picking_id.carrier_id.prod_environment
            easypost.api_key = tracking.picking_id.carrier_id.easypost_account_id._get_easypost_api_key(environment_key)
            try:                    
                shipment = easypost.Shipment.retrieve(tracking.shipping_id)
                values = {}
                values_tracking = {}
                if shipment.get('tracker'):
                    values.update({'tracking_url': shipment['tracker'].get('public_url') or '',
                                'tracking_status': shipment['tracker'].get('status') or '',
                                })
                    if shipment.get('tracker').get('tracking_details'):
                        tracking_details = shipment.get('tracker').get('tracking_details')[-1]
                        if tracking_details.get('tracking_location'):
                            values_tracking.update({'tracking_city': tracking_details['tracking_location'].get('city') or '',
                                            'tracking_state': tracking_details['tracking_location'].get('state') or '',
                                            'tracking_country': tracking_details['tracking_location'].get('country') or '',
                                            'tracking_zip': tracking_details['tracking_location'].get('zip') or '',
                                            'name': tracking_details.get('message') or '',
                                            'shipment': tracking.id
                                            })
                                            
                tracking.write(values)
                self.env['easypost.shipment.tracking'].create(values_tracking)
            except easypost.Error as e:
                if e.json_body and e.json_body.get("error"):
                    errors = ""
                    for error in e.json_body.get("error").get("errors"):
                        errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                    message = e.json_body.get("error").get("message") + '\n\nDetails: ' + errors
                    raise UserError(_(message))
                else:
                    raise UserError(_(e.message))

class Easypostaccount(models.Model):
    _name = 'easypost.account'
    _description = 'EasyPost account info'

    name = fields.Char('name', required=True)
    easypost_api_key = fields.Char('EasyPost API Key')
    easypost_api_key_development = fields.Char('EasyPost Test API Key')
    scanform_prod_environment = fields.Boolean('Use Prod Key for ScanForms', help="If selected the ScanForms will use the Easypost API Key")
    webhook_id = fields.Char('webhook id')
    
    def open_easy_post_accounts(self):
        return {
            'res_model': 'easypost.carrier',
            'type': 'ir.actions.act_window',
            'context': {},
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain':[('easypost_account_id','=',self.id)],
            'target': 'current'
        }
    
    def _get_easypost_api_key(self, prod_environment):
        if prod_environment:
            return str(self.easypost_api_key)
        else:
            return str(self.easypost_api_key_development)
    
    def create_easypost_carrier(self):
        easypost.api_key = self._get_easypost_api_key(True)
        try: 
            carry_type_obj=self.env['easypost.carrier.type']
            carrier_obj=self.env['easypost.carrier']
            
            carrier_accounts = easypost.CarrierAccount.all()
            _logger.info(carrier_accounts)
            
            for carr_obj in carrier_accounts:
                #check to see if carrier alredy exists, if not create it
                carrier = carrier_obj.search([('carrier_account_id', '=', carr_obj.get('id'))], limit=1)
                if not carrier:
                    #checking to see if carrier type is present if not create it
                    carrier_type = carry_type_obj.search([('carrier_type','=',carr_obj.get('type'))],limit=1)
                    if not carrier_type:     
                        carrier_type = carry_type_obj.create({
                            'carrier_type': carr_obj.get('type'),
                            'name': carr_obj.get('readable')
                        })                        
                    carrier_obj.create({
                        'easypost_carrier_type':carrier_type.id,
                        'name':carr_obj.get('readable'),
                        'carrier_account_id':carr_obj.get('id'),
                        'active':True,
                        'easypost_account_id':self.id
                    })
            
        except easypost.Error as e:
            if e.json_body and e.json_body.get("error"):
                errors = ""
                for error in e.json_body.get("error").get("errors"):
                    errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                message = e.json_body.get("error").get("message") + '\n\nDetails: ' + errors
                raise UserError(_(message))
            else:
                raise UserError(_(e.message))
        return True

    def create_easypost_webhook(self):
        try:
            easypost.api_key = self._get_easypost_api_key(True)
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            webhook = easypost.Webhook.create(url=base_url+'/webhook/easypost')
            self.webhook_id = webhook.get('id') or ''
        except easypost.Error as e:
            if e.json_body and e.json_body.get("error"):
                errors = ""
                for error in e.json_body.get("error").get("errors"):
                    errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                message = e.json_body.get("error").get("message") + '\n\nDetails: ' + errors
                raise UserError(_(message))
            else:
                raise UserError(_(e.message))


class EasyPostShipmentTracking (models.Model):
    _name = 'easypost.shipment.tracking'   
    _order = 'id desc'
    _description = 'EasyPost Shipments tracking'

    name = fields.Char('Message') 
    shipment = fields.Many2one('easypost.shipment', 'shipment')
    tracking_city = fields.Char('City')
    tracking_state = fields.Char('State')
    tracking_country = fields.Char('Country')
    tracking_zip = fields.Char('ZIP')
    tracking_time = fields.Datetime('Tracking Time')
    tracking_status = fields.Char('Status', help="""Status of the package at the time of the scan event, possible values are \n"unknown", "pre_transit", "in_transit", "out_for_delivery", "delivered", \n"available_for_pickup", "return_to_sender", "failure", "cancelled" or "error\"""")
