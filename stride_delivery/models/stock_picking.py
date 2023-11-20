import easypost
import requests
import os

from urllib import request
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

import logging

_logger = logging.getLogger(__name__)

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    required_carrier = fields.Boolean(string='Required Carrier')

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_easypost_rate(self):
        shipping_rate_pool = self.env['easypost.shipping.rate']
        shipping_rate_line_pool = self.env['easypost.shipping.rate.line']
        carrier_pool = self.env['delivery.carrier']
        for record in self:
            easypost.api_key = record.carrier_id.easypost_account_id._get_easypost_api_key(record.carrier_id.prod_environment)

            shipping_rate_pool.search([]).unlink()
            shipper = record.picking_type_id.warehouse_id.partner_id
            reciever = record.partner_id
            
            to_address = {
                'name': reciever.name,
                'street1': reciever.street or '',
                'street2': reciever.street2 or '',
                'city': reciever.city or '',
                'state': reciever.state_id and reciever.state_id.name or '',
                'zip': reciever.zip or '',
                'country': reciever.country_id and reciever.country_id.code or '',
                'phone': reciever.phone or ''
                }
            from_address = {
                'name': shipper.name,
                'street1': shipper.street or '',
                'street2': shipper.street2 or '',
                'city': shipper.city or '',
                'state': shipper.state_id and shipper.state_id.name or '',
                'zip': shipper.zip or '',
                'country': shipper.country_id and shipper.country_id.code or '',
                'phone': shipper.phone or ''
                }

            try:
                package_list = []
                shipment = {}
                shipment_id = 0

                #Set Shipment Options
                options = {
                    "label_size": record.carrier_id.easypost_label_size,
                    "label_format": record.carrier_id.file_type,
                    "print_custom_1": record.sale_id.client_order_ref or ''
                }

                if record.carrier_id.use_third_party and record.carrier_id.use_fix_third_party_account:
                    options["payment"] = {
                        "country": reciever.country_id.code,
                        "account": record.carrier_id.bill_third_party_account_number,
                        "type": "THIRD_PARTY",                            
                        "postal_code": record.carrier_id.bill_third_party_zip
                    }

                if record.carrier_id.use_third_party and not record.carrier_id.use_fix_third_party_account and reciever.bill_third_party_account:
                    options["payment"] = {
                        "country": reciever.country_id.code,
                        "account": reciever.bill_third_party_account,
                        "type": "THIRD_PARTY",                            
                        "postal_code": reciever.bill_third_party_zip or reciever.zip
                    }

                if record.add_sat_delivery:
                    options["saturday_delivery"] = True

                if record.add_signature:
                    options["delivery_confirmation"] = "SIGNATURE"  
                
                if record.incoterm_id:
                    options["incoterm"] = record.incoterm_id.code  
                else:
                    options["incoterm"] = self.env.company.incoterm_id.code or 'FOB'
                
                #Options for FedEx international shipments
                if record.carrier_id.use_letterhead:
                    options["commercial_invoice_letterhead"] = "IMAGE_1"
                if record.carrier_id.use_signature:
                    options["commercial_invoice_signature"] = "IMAGE_2"

                #Determine which lines are "put in pack"
                move_lines_with_package = record.move_line_ids.filtered(lambda ml: ml.result_package_id and ml.qty_done)
                move_lines_without_package = record.move_line_ids.filtered(lambda ml: ml.qty_done) - move_lines_with_package

                if not move_lines_with_package and not move_lines_without_package:
                    raise UserError(_("Please update done qty on product lines."))

                if move_lines_without_package:
                    weight = record.shipping_weight or record.weight
                    if weight <= 0:
                        raise UserError(_("Product weight must be greater than 0."))

                    weight = record.carrier_id._weight_to_oz(weight) 
                    custom_items = record.carrier_id._get_custom_details(move_lines_without_package, record)
                    
                    packaging_id = record.packaging_id
                    parcel = {'weight': weight}
                    if packaging_id and packaging_id.packaging_length > 0 and packaging_id.width > 0 and packaging_id.height > 0:
                        parcel.update({'length': record.packaging_id.packaging_length,
                                       'width': record.packaging_id.width,
                                       'height': record.packaging_id.height})

                    shipment = {'0': {'parcel': parcel,
                                      'options': options,
                                      'customs_info': {'eel_pfc': record.eel_pfc or record.carrier_id.eel_pfc,
                                                       'customs_certify': record.carrier_id.customs_certify,
                                                       'customs_signer': record.carrier_id.customs_signer,
                                                       'contents_type': record.carrier_id.contents_type,
                                                       'non_delivery_option': record.carrier_id.non_delivery_option,
                                                       'customs_items': custom_items}}}
                    shipment_id += 1

                for package_line in move_lines_with_package:
                    if package_line.result_package_id not in package_list:
                        package_list.append(package_line.result_package_id)
                        # compute move line weight in package
                        pack_package_lines = record.move_line_ids.filtered(lambda pl: pl.result_package_id == package_line.result_package_id)
                        weight = record.shipping_weight or record.weight
                        weight = record.carrier_id._weight_to_oz(weight) 
                        # Prepare an easypost parcel with same info than package.
                        custom_items = record.carrier_id._get_custom_details(pack_package_lines, record)
                        
                        reference = package_line.result_package_id.name

                        #Add package number to label
                        options["print_custom_2"] = f"""Package: {reference}"""

                        #Set package details
                        packaging_id = package_line.result_package_id.package_type_id
                        if packaging_id.shipper_package_code:
                            parcel = {'weight': record.carrier_id._weight_to_oz(package_line.result_package_id.shipping_weight),
                                        'predefined_package': packaging_id.shipper_package_code}
                        else:
                            parcel = {'weight': record.carrier_id._weight_to_oz(package_line.result_package_id.shipping_weight)}
                            packaging_length = packaging_id.packaging_length if not package_line.result_package_id.package_type_id.customs_package else package_line.result_package_id.custom_length
                            width = packaging_id.width if not package_line.result_package_id.package_type_id.customs_package else package_line.result_package_id.custom_width
                            height = packaging_id.height if not package_line.result_package_id.package_type_id.customs_package else package_line.result_package_id.custom_height
                            if packaging_length > 0 and width > 0 and height > 0:
                                parcel.update({
                                     'length': packaging_length,
                                     'width': width,
                                     'height': height,
                                    })

                        #Add Shipment to the list of shipments
                        shipment.update({'%d' % shipment_id: {
                            'parcel': parcel,
                            'options': options,
                            'reference': reference,
                            'customs_info': {'eel_pfc': record.eel_pfc or record.carrier_id.eel_pfc,
                                            'customs_certify': record.carrier_id.customs_certify,
                                            'customs_signer': record.carrier_id.customs_signer,
                                            'contents_type': record.carrier_id.contents_type,
                                            'non_delivery_option': record.carrier_id.non_delivery_option,
                                            'customs_items': custom_items}}})
                        shipment_id += 1
                    else:
                        continue

                shipments = []
                for ship in shipment.items():
                    shipments.append(ship[1])
                _logger.info(shipments)

                if shipments:
                    order = easypost.Order.create(from_address=from_address, to_address=to_address, shipments=shipments, carrier_accounts=[])

                    if order:
                        _logger.info(order)
                        rates = order.get('rates', False)
                        shipping_rate_id = shipping_rate_pool.create({'stock_picking_id': record.id})
                        for rate in rates:
                            carrier_id = carrier_pool.search([('delivery_type', '=', 'easypost'),
                                ('easypost_carrier_id.easypost_carrier_type', '=', str(rate.get('carrier'))),
                                ('service_level.name', '=', str(rate.get('service')))], limit=1)

                            if carrier_id:
                                line = shipping_rate_line_pool.create({'easypost_shipping_rate_id': shipping_rate_id.id,
                                    'carrier': str(rate.get('carrier')),
                                    'service': str(rate.get('service')),
                                    'est_delivery_days': int(rate.get('est_delivery_days')) if rate.get('est_delivery_days') else 0,
                                    'rate': float(rate.get('rate'))})
                        result = self.env['ir.actions.act_window']._for_xml_id('stride_delivery.easypost_shipping_rate_action')
                        result['views'] = [(False, 'form')]
                        result['res_id'] = shipping_rate_id.id
                        return result
            
            except easypost.Error as e:
                if e.json_body and e.json_body.get("error"):
                    errors = ""
                    for error in e.json_body.get("error").get("errors"):
                        errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                    message = e.json_body.get("error").get("message") + '\n\nDetails: ' + errors
                    raise UserError(_(message))
                else:
                    raise UserError(_(e.message))
                            
    # def get_multiple_carrier_tracking(self):
    #     self.ensure_one()
    #     if not self.ep_shipment_ids:
    #         return super(StockPicking, self).get_multiple_carrier_tracking()
    #     res = []
    #     for shipment in self.ep_shipment_ids.filtered(lambda x: not x.is_return_shipment):
    #         res.append([shipment.name, shipment.tracking_url])
    #     return res

    def get_product_lines(self):
        return self.move_line_ids_without_package.sorted(key=lambda ml: ml.result_package_id.id)

    @api.depends('ep_shipment_ids')
    def _check_is_tracking_available(self):
        for record in self:
            record.is_tracking_available = True if record.ep_shipment_ids else False

    @api.depends('sale_id')
    def _compute_cod_amount(self):
        for record in self:
            record.cod_amount = record.sale_id and record.sale_id.amount_total or 0.0

    attachment_ids = fields.Many2many('ir.attachment', 'res_id', 
                                    domain=lambda self: [('res_model', '=', self._name)], 
                                    auto_join=True, string='Attachments')
    is_easypost_delivery = fields.Boolean('Easypost Delivery', copy=False)
    shipping_id = fields.Char('Shipping ID', copy=False) #This need to remove this - not needed on Picking level
    ep_order_id = fields.Char("Order ID", copy=False)
    ep_shipment_ids = fields.One2many('easypost.shipment', 'picking_id', 'Easypost Tracking Details')
    is_tracking_available = fields.Boolean(string='Tracking Available', compute='_check_is_tracking_available')
    #EasyPost Optional Items
    add_insurance = fields.Boolean('Buy Shipping Insurance')
    add_sat_delivery = fields.Boolean('Request Sat Delivery')
    add_signature = fields.Boolean('Request Adult Sign')
    cash_on_delivery = fields.Boolean('COD')
    cod_amount = fields.Float(string='COD Amount', compute='_compute_cod_amount', readonly=False, store=True)
    cod_method = fields.Selection([('CASH', 'CASH'),
        ('CHECK', 'CHECK'),
        ('MONEY_ORDER', 'MONEY ORDER')], default='CASH', string='COD Method')
    create_return_label = fields.Boolean('Create Return Label')
    incoterm_id = fields.Many2one(related="sale_id.incoterm", 
                                store=True, 
                                readonly=False, 
                                string='Shipping Incoterm', 
                                help="""Incoterm negotiated for shipment. Supported values are "EXW", "FCA", "CPT", "CIP", "DAT", "DAP", "DDP", "FAS", "FOB", "CFR", and "CIF". \n 
                                Setting this value to anything other than "DDP" will pass the cost and responsibility of duties on to the recipient of the package(s), as specified by Incoterms rules""")
    ship_international = fields.Boolean(related="carrier_id.ship_international", store=True)
    eel_pfc = fields.Char(string="EEL or ITN", default="NOEEI 30.37(a)", 
                        help="""When shipping outside the US, you need to provide either an Exemption and Exclusion Legend (EEL) code or a Proof of Filing Citation (PFC). 
                        \n Which you need is based on the value of the goods being shipped.
                        \n - If the value of the goods is less than $2,500, then you pass the following EEL code: "NOEEI 30.37(a)"
                        \n - If the value of the goods is greater than $2,500, you need to get an Automated Export System (AES) Internal Transaction Number (ITN) for your shipment. ITN will look like “AES X20120502123456”. To get an ITN, go to the AESDirect website.
                        \n - An ITN is required for any international shipment valued over $2,500 and/or requires an export license unless exemptions apply.""")
    packaging_id = fields.Many2one(
        'stock.package.type', 'Package Type', index=True, check_company=True)
    customer_contact_no = fields.Char(string='Phone #', related='partner_id.phone')
    required_carrier = fields.Boolean(string='Required Carrier', related='picking_type_id.required_carrier')

    def button_validate(self):
        for record in self:
            if record.carrier_id and record.carrier_id.delivery_type == 'easypost' and record.picking_type_code == 'outgoing' and record.partner_id:
                zip_required = record.partner_id.country_id and record.partner_id.country_id.zip_required or False
                state_required = record.partner_id.country_id and record.partner_id.country_id.state_required or False
                if not record.partner_id.street or not record.partner_id.city or (state_required and not record.partner_id.state_id) or (zip_required and not record.partner_id.zip):
                    if zip_required and state_required:
                        raise UserError(_("Delivery Address is incomplete. Please complete delivery address before confirming (street, city, state, and zip are required)."))
                    elif zip_required and not state_required:
                        raise UserError(_("Delivery Address is incomplete. Please complete delivery address before confirming (street, city, and zip are required)."))
                    elif not zip_required and state_required:
                        raise UserError(_("Delivery Address is incomplete. Please complete delivery address before confirming (street, city, and state are required)."))
                    elif not zip_required and not state_required:
                        raise UserError(_("Delivery Address is incomplete. Please complete delivery address before confirming (street and city are required)."))
        res = super(StockPicking, self).button_validate()
        for record in self:
            if record.company_id.auto_download_shipping_label and record.ep_shipment_ids.filtered(lambda x: x.label_url):
                return record.with_context({'reload': True}).action_download_label()
        return res

    def action_download_label(self):
        for picking in self:
            labels = []
            message_id = self.env['mail.message'].search([('res_id', '=', picking.id),
                ('model', '=', 'stock.picking'), ('attachment_ids', '!=', False)], limit=1, order='id desc')
            attachment_name = message_id and message_id.attachment_ids.mapped('name') or []
            flag = True
            for shipment in picking.ep_shipment_ids.filtered(lambda x: x.label_url):
                label = requests.get(shipment.label_url)
                label_name = 'LabelEasypost-%s.%s' % (shipment.name, picking.carrier_id.file_type)
                labels.append((label_name, label.content))
                if label_name not in attachment_name:
                    flag = False

            if not flag or not message_id:
                logmessage = _("Downloaded Easypost Labels")
                picking.message_post(body=logmessage, attachments=labels)

                message_id = self.env['mail.message'].search([('res_id', '=', picking.id),
                    ('model', '=', 'stock.picking'), ('attachment_ids', '!=', False)], limit=1, order='id desc')
            
            action_list = [{'type': 'ir.actions.act_window_close'}]
            if self.env.context.get('reload'):
                action_list.append({'type': 'ir.actions.client', 'tag': 'reload'})
            for attachment in message_id.attachment_ids:
                action_list.append({
                    'type': 'ir.actions.act_url',
                    'url': "web/content/?model=ir.attachment&id=" + str(attachment.id) + "&filename_field=name&field=datas&download=true&name=" + attachment.name,
                    'target': 'new'
                })
            if action_list:
                return {
                    'type': 'ir.actions.act_multi',
                    'actions': action_list
                 }

    @api.model_create_multi
    def create(self, vals_list):
        records = super(StockPicking, self).create(vals_list)
        for record in records:
            if record.carrier_id:
                record.write({'add_insurance': record.carrier_id.add_insurance, 'add_sat_delivery': record.carrier_id.add_sat_delivery,
                    'add_signature': record.carrier_id.add_signature, 'eel_pfc': record.carrier_id.eel_pfc,
                    'packaging_id': record.carrier_id.packaging_id, 'create_return_label': record.carrier_id.create_return_label,
                    'cash_on_delivery': record.carrier_id.cash_on_delivery})
        return records

    @api.onchange('carrier_id')
    def _onchange_carrier_id(self):
        if self.carrier_id:
            self.write({
                'add_insurance': self.carrier_id.add_insurance,
                'add_sat_delivery': self.carrier_id.add_sat_delivery,
                'add_signature': self.carrier_id.add_signature,
                'eel_pfc': self.carrier_id.eel_pfc,
                'create_return_label': self.carrier_id.create_return_label,
                'packaging_id': self.carrier_id.packaging_id,
                'cash_on_delivery': self.carrier_id.cash_on_delivery
            })

    def update_tracking_button(self):
        for picking in self:
            picking.ep_shipment_ids.request_tracking_details()
    
    def create_missing_tracking_details(self):
        for picking in self:
            environment_key = picking.carrier_id.prod_environment
            easypost.api_key = picking.company_id._get_easypost_api_key(environment_key)
            try:                    
                confirmed_order = easypost.Order.retrieve(picking.ep_order_id)
                for shipment in confirmed_order.shipments:
                    picking.carrier_id.create_tracking_details(picking, shipment)
            except easypost.Error as e:
                if e.json_body and e.json_body.get("error"):
                    errors = ""
                    for error in e.json_body.get("error").get("errors"):
                        errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                    message = e.json_body.get("error").get("message") + '\n\nDetails: ' + errors
                    raise UserError(_(message))
                else:
                    raise UserError(_(e.message))

    def send_easypost_confirmation_email(self):
        for picking in self:
            delivery_template_id =  self.env.ref('stock.mail_template_data_delivery_confirmation').id
            picking.with_context(force_send=True).message_post_with_template(delivery_template_id, email_layout_xmlid='mail.mail_notification_light')
