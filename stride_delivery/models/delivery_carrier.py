import json
import easypost
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timezone
import logging

_logger = logging.getLogger(__name__)

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('easypost', 'Easypost')], ondelete={'easypost': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    easypost_carrier_id = fields.Many2one('easypost.carrier', 'Carrier Name')
    file_type = fields.Selection([('PNG', 'PNG'), ('PDF', 'PDF'), ('ZPL', 'ZPL'), ('EPL2', 'EPL2')], 'Label File Type', default='PDF')
    service_level = fields.Many2one('easypost.service.level', 'Service Level')
    use_third_party = fields.Boolean(string="Use Third Party Billing")
    use_fix_third_party_account = fields.Boolean(string="Use Fix Third Party Account")
    bill_third_party_account_number = fields.Char(string='Billing Account Number')
    bill_third_party_zip = fields.Char(string="Billing Account ZIP")
    ship_international = fields.Boolean(help="Check if you use this carrier/service level for international shipments")

    #Global Options - Can be overriden on the Picking Level
    add_insurance = fields.Boolean('Buy Shipping Insurance')
    insurance_calculation = fields.Selection([('sale', 'Based On Sale Price'),
        ('cost', 'Based On Cost Price')], default='sale', string='Insurance Price Calculation')
    add_sat_delivery = fields.Boolean('Request Sat Delivery')
    add_signature = fields.Boolean('Request Adult Sign')
    mail_our_delivery = fields.Boolean('Out for Delivery Email Notification')
    mail_delivered = fields.Boolean('Delivered Email Notification')
    sms_our_delivery = fields.Boolean('Out for Delivery SMS Notification')
    sms_delivered = fields.Boolean('Delivered SMS Notification')
    create_return_label = fields.Boolean('Create Return Label')
    cash_on_delivery = fields.Boolean('COD')

    #customsInfo
    easypost_label_size =fields.Selection([("4x6","4x6"),("4x7","4x7"),("4x8","4x8")], default='4x6', help="Lable size")
    contents_type = fields.Selection([("merchandise","Merchandise"),("documents","Documents"),("gift","Gifts"),("returned_goods","Returned Goods"),("sample","Samples")], default='merchandise', help="What type of items are you shipping")
    non_delivery_option = fields.Selection([("return","Return"),("abandon","Abandon")], default='return', help="What would you like to do with undeliverable shipments")
    customs_certify = fields.Boolean(default=True)
    quote_max_weight = fields.Float("Quote Max Weight")
    customs_signer = fields.Char(default=lambda self: self.env.company.name)
    eel_pfc = fields.Char(string="EEL or ITN", default="NOEEI 30.37(a)", 
                        help="""When shipping outside the US, you need to provide either an Exemption and Exclusion Legend (EEL) code or a Proof of Filing Citation (PFC). 
                        \n Which you need is based on the value of the goods being shipped.
                        \n - If the value of the goods is less than $2,500, then you pass the following EEL code: "NOEEI 30.37(a)"
                        \n - If the value of the goods is greater than $2,500, you need to get an Automated Export System (AES) Internal Transaction Number (ITN) for your shipment. ITN will look like “AES X20120502123456”. To get an ITN, go to the AESDirect website.
                        \n - An ITN is required for any international shipment valued over $2,500 and/or requires an export license unless exemptions apply.""")
    use_letterhead = fields.Boolean(help='Check this box if you would like to use your custom letterhead for customs froms \nPlease note these need to be sent to and setup by EasyPost \nThis needs to be "IMAGE_1"')
    use_signature = fields.Boolean(help='Check this box if you would like to use your custom signature for customs forms\nPlease note these need to be sent to and setup by EasyPost \nThis needs to be "IMAGE_2"')
    easypost_account_id = fields.Many2one('easypost.account', 'Easypost Account')
    easypost_carrier_type = fields.Many2one('easypost.carrier.type', 'Easypost Carrier Type', related="easypost_carrier_id.easypost_carrier_type", store=True)
    packaging_id = fields.Many2one(
        'stock.package.type', 'Package Type', index=True, check_company=True)
    
    @api.onchange('easypost_account_id')
    def onchange_easypost_account_id(self):
        self.easypost_carrier_id = False

    @api.onchange('easypost_carrier_id')
    def onchange_easypost_carrier_id(self):
        self.service_level = False

    def _weight_to_oz(self, weight):
        if self.env['ir.config_parameter'].sudo().get_param('product.weight_in_lbs') == '1':
            converted_weight = weight * 16
        else:
            converted_weight = weight * 35.274
        return converted_weight
    
    def _compute_can_generate_return(self):
        super(DeliveryCarrier, self)._compute_can_generate_return()
        for carrier in self:
            if carrier.delivery_type == 'easypost':
                carrier.can_generate_return = False
    
    def _compute_true_customs_value(self, line):
        """Uses the value from the SO to compute the value the product was actually sold at for customs calculation. \n
        Value returned is the per unit value. Coupons are not taken into account and are ignored for exporting purposes"""
        sale_line = line.move_id.sale_line_id
        if sale_line:
            mrp_module = self.env['ir.model.fields'].sudo().search([('name', '=', 'bom_line_id'), ('model_id.model', '=', 'stock.move')], limit=1)
            if mrp_module and line.move_id.bom_line_id:
                total_kit_value = 0.0
                sale_value = sale_line.price_subtotal / sale_line.product_uom_qty
                for move_line in line.picking_id.move_ids.filtered(lambda x: x.sale_line_id == line.move_id.sale_line_id):
                    if move_line.product_id.standard_price:
                        total_kit_value += (move_line.product_id.standard_price * move_line.quantity_done)

                if line.product_id.standard_price and total_kit_value:
                    value = (line.product_id.standard_price/total_kit_value) * sale_value
                    return value
                else:
                    return sale_value
            else:
                value = 0
                if sale_line.product_uom_qty > 0: 
                    value = sale_line.price_subtotal / sale_line.product_uom_qty
                return value
        else:
            return False
    
    def _get_custom_details(self, pack_lines, picking):
        customs_items = []
        for line in pack_lines:
            if line.product_id.type not in ['product', 'consu']:
                continue
            unit_quantity = line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id,
                                                                  rounding_method='HALF-UP') 
            true_customs_value = self._compute_true_customs_value(line)
            details = {'description': line.product_id.name + '-' +str(line.product_id.id),
                        'quantity': unit_quantity,
                        'origin_country': line.product_id.country_of_origin.code or picking.company_id.country_id.code,
                        'value': true_customs_value * unit_quantity or line.product_id.lst_price * unit_quantity,
                        'weight': self._weight_to_oz(unit_quantity * line.product_id.weight),
                        'hs_tariff_number': line.product_id.hs_code}
            
            if not unit_quantity.is_integer():
               details.update({'description': line.product_id.name +" (" + str(unit_quantity) + " "+ str(line.product_uom_id.name) + ")",
                                'quantity': 1,
                                })
            customs_items.append(details)
        return customs_items
    
    def easypost_rate_shipment(self, order):
        easypost.api_key = self.easypost_account_id._get_easypost_api_key(self.prod_environment)

        shipper = order.warehouse_id.partner_id
        reciever = order.partner_shipping_id
        
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
            items=[]
            for line in order.order_line:
                if not line.is_delivery and line.product_id.type != "service" and line.product_id.weight <= 0:
                    raise UserError(_("Product: %s's weight must be greater than 0." % line.product_id.display_name))
                elif not line.is_delivery and line.product_id.type != "service":                    
                    if line.product_id.weight > self.quote_max_weight:
                        raise UserError(_("Product: %s's weight (%s) is greater then allowed for this shipping method. \nPlease select a shipping method that allows a higher per package weight." % (line.product_id.display_name, line.product_id.weight)))
                    items.append({'name':line.product_id.name,
                        'origin_country':line.product_id.country_of_origin.code or order.company_id.country_id.code,
                        'quantity':line.product_uom_qty,
                        'value':line.price_total,
                        'product_id':line.product_id,
                        'line':line,
                        'weight':line.product_id.weight,
                        'hs_tariff_number':line.product_id.hs_code                    
                    })                   
            
            single_list=[]
            newlist = sorted(items, key=lambda d: d['weight']) 
            for cust in newlist:
                single_list.extend([cust]*int(cust['quantity']))  
            _logger.info(single_list)         
            
            shipments = {}
            shipment_id = 0            
            we = 0
            custom_items=[]           
            
            options = { }
            if self.use_third_party:
                if self.use_fix_third_party_account:
                    options["payment"] = {
                        "country": order.partner_id.country_id.code,
                        "account": self.bill_third_party_account_number,
                        "type": "THIRD_PARTY",                            
                        "postal_code": self.bill_third_party_zip
                    }
                if not self.use_fix_third_party_account and order.partner_id.bill_third_party_account:
                    options["payment"] = {
                        "country": order.partner_id.country_id.code,
                        "account": order.partner_id.bill_third_party_account,
                        "type": "THIRD_PARTY",                            
                        "postal_code": order.partner_id.bill_third_party_zip or order.partner_id.zip
                    }

            for prod in single_list:
                we = we + prod['weight']
                if we < self.quote_max_weight:                     
                    custom_items.append({'description': prod['line'].product_id.name,
                                  'origin_country': prod['line'].product_id.country_of_origin.code or shipper.country_id.code,
                                  'quantity': 1,
                                  'value': prod['line'].product_id.lst_price * 1,
                                  'weight':  self._weight_to_oz(prod['weight']),
                                  'hs_tariff_number': prod['line'].product_id.hs_code})
                    
                    shipments[str(shipment_id)]={'parcel': {'weight': self._weight_to_oz(we)},
                                                'options': options,
                                                'customs_info': {'eel_pfc': self.eel_pfc,
                                                                'customs_certify': self.customs_certify,
                                                                'customs_signer': self.customs_signer,
                                                                'contents_type': self.contents_type,
                                                                'non_delivery_option': self.non_delivery_option,
                                                                'customs_items': custom_items}}
                else:
                    shipment_id = shipment_id + 1
                    we = prod['weight']
                    custom_items.append({'description': prod['line'].product_id.name,
                                  'origin_country': prod['line'].product_id.country_of_origin.code or shipper.country_id.code,
                                  'quantity': 1,
                                  'value': prod['line'].product_id.lst_price * 1,
                                  'weight': self._weight_to_oz(prod['weight']),
                                  'hs_tariff_number': prod['line'].product_id.hs_code})
                    shipments[str(shipment_id)]={'parcel': {'weight': self._weight_to_oz(we)},
                                                'options': options,
                                                'customs_info': {'eel_pfc': self.eel_pfc,
                                                                'customs_certify': self.customs_certify,
                                                                'customs_signer': self.customs_signer,
                                                                'contents_type': self.contents_type,
                                                                'non_delivery_option': self.non_delivery_option,
                                                                'customs_items': custom_items}}
            _logger.info(shipments)
            shipment = easypost.Order.create(to_address=to_address, from_address=from_address, shipments=shipments, carrier_accounts=[self.easypost_carrier_id.carrier_account_id])
            
            if shipment:
                rates = shipment.get('rates', False)
                if not rates:
                    error_message = shipment.get('messages', False)
                    if error_message:
                        message = error_message[0].get('message', False)
                    else:
                        message = "Rates not available."
                    return {'success': False,
                            'price': 0.0,
                            'error_message': message,
                            'warning_message': False}

                selected_rate = False
                rate_price = 0
                for rate in rates:
                    #_logger.info(f"EasyPost Quoted Rates: {rate}")
                    if rate.carrier_account_id == self.easypost_carrier_id.carrier_account_id and rate.service == self.service_level.name:
                        selected_rate = rate
                        rate_price=rate_price +float(rate['rate'])
                if selected_rate:
                    if order.currency_id.name == selected_rate['currency']:
                        price = rate_price
                    else:
                        ep_currency = self.env['res.currency'].search([('name', '=', selected_rate['currency'])], limit=1)
                        price = ep_currency._convert(rate_price), order.currency_id, self.env.company, fields.Date.today()
                    if self.use_third_party and (self.use_fix_third_party_account or order.partner_id.bill_third_party_account):
                        return {'success': True,
                                'price': 0.0,
                                'error_message': False,
                                'no_of_packages': len(shipments),
                                'warning_message': "Third Party Billing - No Charge"}
                    else:
                        return {'success': True,
                                'price': price,
                                'no_of_packages': len(shipments),
                                'error_message': False,
                                'warning_message': False}
                else:
                    return {'success': False,
                            'price': 0.0,
                            'error_message': "Defined service is not available",
                            'warning_message': False}
           
        except easypost.Error as e:
            if e.json_body and e.json_body.get("error"):
                errors = ""
                for error in e.json_body.get("error").get("errors"):
                    errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                message = e.json_body.get("error").get("message") + '\n\nDetails : ' + errors
                raise UserError(_(message))
            else:
                raise UserError(_(e.message))

    def easypost_send_shipping(self, pickings):
        res = []
        for picking in pickings:            
            if picking.picking_type_id.code == 'outgoing':
                #Set basic Order Details
                easypost.api_key = self.easypost_account_id._get_easypost_api_key(self.prod_environment)

                shipper = picking.picking_type_id.warehouse_id.partner_id
                reciever = picking.partner_id
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
                if reciever.company_type == 'person':
                    if reciever.parent_id and reciever.parent_id.company_type == 'company':
                        to_address['company'] = reciever.parent_id.name

                from_address = {
                    'name': shipper.name,
                    'company': shipper.name,
                    'street1': shipper.street or '',
                    'street2': shipper.street2 or '',
                    'city': shipper.city or '',
                    'state': shipper.state_id and shipper.state_id.name or '',
                    'zip': shipper.zip or '',
                    'country': shipper.country_id and shipper.country_id.code or '',
                    'phone': shipper.phone or ''
                }
                # Create Shipments to include in Easypost Order
                if not picking.ep_order_id:
                    try:
                        package_list = []
                        shipment = {}
                        shipment_id = 0

                        #Set Global Shipment Options
                        options = {
                                'label_size': self.easypost_label_size,
                                "label_format": picking.carrier_id.file_type,
                                "print_custom_1": picking.sale_id.client_order_ref or ''
                                }
                        if picking.carrier_id.use_third_party and picking.carrier_id.use_fix_third_party_account:
                            options["payment"] = {
                                "country": reciever.country_id.code,
                                "account": picking.carrier_id.bill_third_party_account_number,
                                "type": "THIRD_PARTY",                            
                                "postal_code": picking.carrier_id.bill_third_party_zip
                            }

                        if picking.carrier_id.use_third_party and not picking.carrier_id.use_fix_third_party_account and reciever.bill_third_party_account:
                            options["payment"] = {
                                "country": reciever.country_id.code,
                                "account": reciever.bill_third_party_account,
                                "type": "THIRD_PARTY",                            
                                "postal_code": reciever.bill_third_party_zip or reciever.zip
                            }
                        if picking.add_sat_delivery:
                            options["saturday_delivery"] = True

                        if picking.add_signature:
                            options["delivery_confirmation"] = "SIGNATURE"
                                            
                        if picking.incoterm_id:
                            options["incoterm"] = picking.incoterm_id.code  
                        else:
                            options["incoterm"] = self.env.company.incoterm_id.code or 'FOB'
                        #Options for FedEx international shipments
                        if picking.carrier_id.use_letterhead:
                            options["commercial_invoice_letterhead"] = "IMAGE_1"
                        if picking.carrier_id.use_signature:
                            options["commercial_invoice_signature"] = "IMAGE_2"

                        #Determine which lines are "put in pack"
                        move_lines_with_package = picking.move_line_ids.filtered(lambda ml: ml.result_package_id)
                        move_lines_without_package = picking.move_line_ids - move_lines_with_package

                        if move_lines_without_package:
                            weight = picking.shipping_weight or picking.weight
                            if weight <= 0:
                                raise UserError(_("Product weight must be greater than 0."))

                            weight = self._weight_to_oz(weight) 
                            custom_items = self._get_custom_details(move_lines_without_package, picking)

                            package_options = {}
                            #Only add COD to frist package in a shipment
                            if shipment_id == 0 and picking.cash_on_delivery:
                                package_options["cod_amount"] = str(picking.cod_amount)
                                package_options["cod_method"] = picking.cod_method or 'CASH'
                                                            
                            packaging_id = picking.packaging_id
                            parcel = {'weight': weight}
                            if packaging_id and packaging_id.packaging_length > 0 and packaging_id.width > 0 and packaging_id.height > 0:
                                parcel.update({'length': picking.packaging_id.packaging_length,
                                               'width': picking.packaging_id.width,
                                               'height': picking.packaging_id.height})

                            shipment = {'%d' % shipment_id: {'parcel': parcel,
                                              'options': {**options,**package_options},
                                              'customs_info': {'eel_pfc': picking.eel_pfc or self.eel_pfc,
                                                               'customs_certify': self.customs_certify,
                                                               'customs_signer': self.customs_signer,
                                                               'contents_type': self.contents_type,
                                                               'non_delivery_option': self.non_delivery_option,
                                                               'customs_items': custom_items}}}
                            shipment_id += 1

                        if move_lines_with_package:
                            for package_line in move_lines_with_package:
                                if package_line.result_package_id not in package_list:
                                    package_list.append(package_line.result_package_id)
                                    # compute move line weight in package
                                    pack_package_lines = picking.move_line_ids.filtered(lambda pl: pl.result_package_id == package_line.result_package_id)
                                    weight = picking.shipping_weight or picking.weight
                                    weight = self._weight_to_oz(weight) 
                                    # Prepare an easypost parcel with same info than package.
                                    custom_items = self._get_custom_details(pack_package_lines, picking)
                                    
                                    reference = package_line.result_package_id.name
                                    
                                    #Add package number to label
                                    package_options = {"print_custom_2": f"""Package: {reference}"""}

                                    #Only add COD to frist package in a shipment
                                    if shipment_id == 0 and picking.cash_on_delivery:
                                        package_options["cod_amount"] = str(picking.cod_amount)
                                        package_options["cod_method"] = picking.cod_method or 'CASH'

                                    #Set package details
                                    packaging_id = package_line.result_package_id.package_type_id
                                    if packaging_id.shipper_package_code:
                                        parcel = {'weight': self._weight_to_oz(package_line.result_package_id.shipping_weight),
                                                    'predefined_package': packaging_id.shipper_package_code}
                                    else:
                                        parcel = {'weight': self._weight_to_oz(package_line.result_package_id.shipping_weight)}
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
                                    shipment.update({'%d' % shipment_id: {'parcel': parcel,
                                                                            'options': {**options,**package_options},
                                                                            'reference': reference,
                                                                            'customs_info': {'eel_pfc': picking.eel_pfc or self.eel_pfc,
                                                                                            'customs_certify': self.customs_certify,
                                                                                            'customs_signer': self.customs_signer,
                                                                                            'contents_type': self.contents_type,
                                                                                            'non_delivery_option': self.non_delivery_option,
                                                                                            'customs_items': custom_items}}})
                                    shipment_id += 1
                                else:
                                    continue

                        _logger.info(shipment)
                        shipments = []
                        for ship in shipment.items():
                            shipments.append(ship[1])
                        if shipments:
                            #Create Easypost Order But does not puchase until after additional verification
                            order = easypost.Order.create(to_address=to_address, from_address=from_address, shipments=shipments,carrier_accounts=[{"id":picking.carrier_id.easypost_carrier_id.carrier_account_id}])
                            if order:
                                rates = order.get('rates', False)
                                if not rates:
                                    error_message = order.get('messages', False)
                                    if error_message:
                                        message = error_message[0].get('message', False)
                                        raise UserError(_(message))
                                    else:
                                        raise UserError(_("Rates not available."))
                                selected_rate = False
                                for rate in rates:
                                    if rate.carrier_account_id == picking.carrier_id.easypost_carrier_id.carrier_account_id and rate.service == picking.carrier_id.service_level.name:
                                        selected_rate = rate
                                shipment_response = order.get('shipments', False)
                                shipping_response_ids = False
                                for ship in shipment_response:
                                    if not shipping_response_ids:
                                        shipping_response_ids = ship.id
                                    else:
                                        shipping_response_ids = ''.join([shipping_response_ids, ',', ship.id])
                                if selected_rate:
                                    picking.write({
                                        'ep_order_id': order['id'],
                                        'shipping_id': shipping_response_ids,
                                    })
                                else:
                                    raise UserError(_("Defined service is not available"))
                    except easypost.Error as e:
                        if e.json_body and e.json_body.get("error"):
                            errors = ""
                            for error in e.json_body.get("error").get("errors"):
                                errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                            message = e.json_body.get("error").get("message") + '\n\nDetails: ' + errors
                            raise UserError(_(message))
                        else:
                            raise UserError(_(e.message))
                        
                    try:
                        #Acutally Purcahse shipping
                        order = easypost.Order.retrieve(picking.ep_order_id)
                        order.buy(carrier=self.easypost_carrier_id.name, service=self.service_level.name)
                        #removes any existing linked tracking ID
                        tracking_ids = self.env['easypost.shipment'].search([('picking_id', '=', picking.id)])
                        tracking_ids.unlink()
                        #Get shipping Lable, create/update tracking ids, and retrieves any custom froms
                        confirmed_order = easypost.Order.retrieve(picking.ep_order_id)
                        _logger.info(f"""Confirmed EasyPost Order: {confirmed_order}""")

                        picking.write({'is_easypost_delivery': True})
                        _logger.info("EasyPost Order Completed")
                        for shipment in confirmed_order.shipments:
                            _logger.info(f"""Confirmed Easypost Shipment {shipment}""")
                            
                            self.create_tracking_details(picking, shipment, return_shipment=False)
                            _logger.info("label tracking detials created")

                            self.get_customs_form(picking, shipment)  
                            _logger.info("customs form completed")

                        #Retrieve the cost of the shipment
                        selected_rate = 0
                        if confirmed_order.get('rates'):
                            rates = confirmed_order.get('rates')                            
                            for rate in rates:
                                if rate.carrier_account_id == self.easypost_carrier_id.carrier_account_id and rate.service == self.service_level.name:
                                    selected_rate = rate

                        _logger.info(f"""Selected Rate: {selected_rate}""")

                        shipping_data = {'exact_price': float(selected_rate['rate']),
                                         'tracking_number': False} #shipment.get('tracker').get('tracking_code')} # 
                        res += [shipping_data]

                    except Exception as e:
                        raise UserError(_("There Was an Error Creating The label\n" + str(e)))

                    try:
                        for shipment in confirmed_order.shipments:
                            #check to see if insurance is required and if so, buy insurance on shipment
                            if picking.add_insurance:
                                self.buy_insurance(picking, shipment)
                    except Exception as e:
                        self.env.cr.commit()
                        raise UserError(_("There Was an Error Buy Insurance\n" + str(e)))

                else:
                    raise UserError(_("EasyPost Order Already Created, Please Cancel Existing Order First"))

                if picking.create_return_label:
                    self.create_return_shipment(picking)
        return res

    def create_return_shipment(self, pickings):
        for picking in pickings:
            easypost.api_key = self.easypost_account_id._get_easypost_api_key(self.prod_environment)

            shipper = picking.partner_id
            reciever = picking.picking_type_id.warehouse_id.partner_id
            
            to_address = {
                'name': shipper.name,
                'street1': shipper.street or '',
                'street2': shipper.street2 or '',
                'city': shipper.city or '',
                'state': shipper.state_id and shipper.state_id.name or '',
                'zip': shipper.zip or '',
                'country': shipper.country_id and shipper.country_id.code or '',
                'phone': shipper.phone or ''
            }

            if shipper.company_type == 'person':
                if shipper.parent_id:
                    to_address['company'] = shipper.parent_id.name
                else:
                    to_address['company'] = shipper.name
            else:
                to_address['company'] = shipper.name
            
            from_address = {
                'name': reciever.name,
                'company': reciever.name,
                'street1': reciever.street or '',
                'street2': reciever.street2 or '',
                'city': reciever.city or '',
                'state': reciever.state_id and reciever.state_id.name or '',
                'zip': reciever.zip or '',
                'country': reciever.country_id and reciever.country_id.code or '',
                'phone': reciever.phone or ''
            }

            parcel_list = []
            package_list = []
            #Determine which lines are "put in pack"
            move_lines_with_package = picking.move_line_ids.filtered(lambda ml: ml.result_package_id)
            move_lines_without_package = picking.move_line_ids - move_lines_with_package

            #Set Shipment Options
            options = {
                "label_size": self.easypost_label_size,
                "label_format": picking.carrier_id.file_type,
                "print_custom_1": picking.sale_id.client_order_ref or ''
                }
            if picking.carrier_id.use_third_party and picking.carrier_id.use_fix_third_party_account:
                options["payment"] = {
                    "country": reciever.country_id.code,
                    "account": picking.carrier_id.bill_third_party_account_number,
                    "type": "THIRD_PARTY",                            
                    "postal_code": picking.carrier_id.bill_third_party_zip
                }

            if picking.carrier_id.use_third_party and not picking.carrier_id.use_fix_third_party_account and reciever.bill_third_party_account:
                options["payment"] = {
                    "country": reciever.country_id.code,
                    "account": reciever.bill_third_party_account,
                    "type": "THIRD_PARTY",                            
                    "postal_code": reciever.bill_third_party_zip or reciever.zip
                }
            if picking.add_sat_delivery:
                options["saturday_delivery"] = True

            if picking.add_signature:
                options["delivery_confirmation"] = "SIGNATURE"  
            
            if picking.incoterm_id:
                options["incoterm"] = picking.incoterm_id.code  
            else:
                options["incoterm"] = self.env.company.incoterm_id.code or 'FOB'
            #Options for FedEx international shipments
            if picking.carrier_id.use_letterhead:
                options["commercial_invoice_letterhead"] = "IMAGE_1"
            if picking.carrier_id.use_signature:
                options["commercial_invoice_signature"] = "IMAGE_2"

            if move_lines_without_package:
                weight = picking.shipping_weight or picking.weight
                if weight <= 0:
                    raise UserError(_("Product weight must be greater than 0."))

                weight = self._weight_to_oz(weight) 

                custom_items = self._get_custom_details(move_lines_without_package, picking)

                customs_info = {'eel_pfc': picking.eel_pfc or self.eel_pfc,
                                'customs_certify': self.customs_certify,
                                'customs_signer': self.customs_signer,
                                'contents_type': self.contents_type,
                                'non_delivery_option': self.non_delivery_option,
                                'customs_items': custom_items}

                packaging_id = picking.packaging_id
                parcel = {'weight': weight}
                if packaging_id and packaging_id.packaging_length > 0 and packaging_id.width > 0 and packaging_id.height > 0:
                    parcel.update({'length': packaging_id.packaging_length, 'width': packaging_id.width or 0,
                                   'height': packaging_id.height or 0})

                try:
                    return_shipment = easypost.Shipment.create(from_address=from_address, to_address=to_address, parcel=parcel, is_return=True, options=options, customs_info=customs_info)
                    shipment = easypost.Shipment.retrieve(return_shipment['id'])
                    shipment.buy(carrier=self.easypost_carrier_id.name, service=self.service_level.name, rate=shipment.lowest_rate())
                    self.create_tracking_details(picking, shipment, return_shipment=True)
                except easypost.Error as e:
                    if e.json_body and e.json_body.get("error"):
                        errors = ""
                        for error in e.json_body.get("error").get("errors"):
                            errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                        message = e.json_body.get("error").get("message") + '\n\nDetails: ' + errors
                        raise UserError(_(message))
                    else:
                        raise UserError(_(e.message))
                
            if move_lines_with_package:
                for package_line in move_lines_with_package:
                    if package_line.result_package_id not in package_list:
                        package_list.append(package_line.result_package_id)
                        
                        pack_package_lines = picking.move_line_ids.filtered(lambda pl: pl.result_package_id == package_line.result_package_id)
                        custom_items = self._get_custom_details(pack_package_lines, picking)

                        reference = package_line.result_package_id.name

                        customs_info = {'eel_pfc': picking.eel_pfc or self.eel_pfc,
                                        'customs_certify': self.customs_certify,
                                        'customs_signer': self.customs_signer,
                                        'contents_type': self.contents_type,
                                        'non_delivery_option': self.non_delivery_option,
                                        'customs_items': custom_items}

                        #Set package details
                        packaging_id = package_line.result_package_id.package_type_id
                        parcel = {'weight': self._weight_to_oz(package_line.result_package_id.shipping_weight)}
                        if packaging_id.packaging_length > 0 and packaging_id.width > 0 and packaging_id.height > 0:
                            parcel.update({'length': packaging_id.packaging_length, 'width': packaging_id.width,
                                           'height': packaging_id.height})
                        
                        try:
                            return_shipment = easypost.Shipment.create(from_address=from_address, to_address=to_address, parcel=parcel, is_return=True, options=options, customs_info=customs_info, reference=reference)
                            shipment = easypost.Shipment.retrieve(return_shipment['id'])
                            shipment.buy(carrier=self.easypost_carrier_id.name, service=self.service_level.name, rate=shipment.lowest_rate())
                            self.create_tracking_details(picking, shipment, return_shipment=True)
                        except easypost.Error as e:
                            if e.json_body and e.json_body.get("error"):
                                errors = ""
                                for error in e.json_body.get("error").get("errors"):
                                    errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                                message = e.json_body.get("error").get("message") + '\n\nDetails: ' + errors
                                raise UserError(_(message))
                            else:
                                raise UserError(_(e.message))

    def easypost_get_tracking_link(self, picking):
        tracking_urls = []
        if picking.ep_shipment_ids:
            for shipment in picking.ep_shipment_ids.filtered(lambda x: not x.is_return_shipment):
                if shipment.get_tracking_url():
                    tracking_urls.append([shipment.name, shipment.get_tracking_url()])
        if tracking_urls:
            return len(tracking_urls) == 1 and tracking_urls[0][1] or json.dumps(tracking_urls)
        else:
            return False

    def easypost_cancel_shipment(self, pickings):
        for picking in pickings:
            easypost.api_key = self.easypost_account_id._get_easypost_api_key(self.prod_environment)
            #Requests label refund on all shipments on this picking
            for tracking in picking.ep_shipment_ids:
                try:
                    shipment = easypost.Shipment.retrieve(tracking.shipping_id)
                    shipment.refund()
                    refund_status = shipment.get('refund_status')
                    if refund_status:
                        tracking.refund_status = refund_status
                except easypost.Error as e:
                    if e.json_body and e.json_body.get("error"):
                        errors = ""
                        for error in e.json_body.get("error").get("errors"):
                            errors += str(error.get('field', "")) +" - "+ str(error.get('message', "Unknown Error"))
                        message = e.json_body.get("error").get("message") + '\n\nDetails: ' + errors
                        raise UserError(_(message))
                    else:
                        raise UserError(_(e.message))
            #Ensure that all shipments on Picking have been successfully refunded before removing them from picking
            all_refunded = False
            for tracking in picking.ep_shipment_ids:                
                if tracking.refund_status == 'not_applicable' or tracking.refund_status == 'rejected':
                    all_refunded = False
                    break
                else:
                    all_refunded = True
            if all_refunded:
                picking.write({
                            'is_easypost_delivery' : False,
                            'ep_order_id' : "",
                            'shipping_id' : "",
                            "carrier_price" : False
                            })

    def create_tracking_details(self, picking, shipment, return_shipment=None):
        values = {}
        tracking_code = shipment['tracking_code'] if shipment['tracking_code'] else "Not Provided"
        values.update({'picking_id': picking.id, 'shipping_id': shipment['id'], 'name': tracking_code})

        if shipment.get("selected_rate")["rate"]:
            values["rate"] = shipment.get("selected_rate")["rate"]
        if shipment.get('reference'):
            package_id = self.env['stock.quant.package'].search([('name', '=like', str(shipment.get('reference')))],limit=1).ids
            values['package_id'] = package_id[0]        
        if shipment.get('tracker'):
            values.update({'tracking_url': shipment['tracker'].get('public_url') or '',
                           'tracking_status': shipment['tracker'].get('status') or '',
                         })
            if shipment['tracker'].get('est_delivery_date'):
                est_delivery_date = datetime.fromisoformat(shipment['tracker']['est_delivery_date'][:-1]).astimezone(timezone.utc)
                est_delivery_date = est_delivery_date.strftime('%Y-%m-%d %H:%M:%S')
                values.update({'est_delivery_date': est_delivery_date})

        if shipment.get('options').get('label_format'):
            url = ''
            label_format = shipment.get('options').get('label_format')
            if label_format == "PDF":
                url = shipment.get('postage_label').get('label_pdf_url')
            elif label_format == "PNG":
                url = shipment.get('postage_label').get('label_url')
            elif label_format == "ZPL":
                url = shipment.get('postage_label').get('label_zpl_url')
            else:
                url = shipment.get('postage_label').get('label_url')        
            values.update({'label_url': url})
        else:
            if shipment.get('postage_label') and shipment.get('postage_label').get('label_url'):
                values.update({'label_url': shipment.get('postage_label').get('label_url')})
        if return_shipment:
            values.update({'is_return_shipment': True})

        self.env['easypost.shipment'].create(values)

    def get_customs_form(self, picking, shipment):
        forms = False
        if shipment.get('forms'):
            forms = shipment.get('forms')
        tracking_id = self.env['easypost.shipment'].search([
                                                            ('picking_id', '=', picking.id),
                                                            ('shipping_id', '=', shipment['id'])
                                                            ], limit=1)
        values = {}
        if forms:
            for form in forms:
                if form.get('form_type') == "commercial_invoice":
                    values.update({
                            'customs_form_url': form.get('form_url'),
                            'submit_elec': 'yes' if form.get('submitted_electronically') else 'no'
                            })
        else:
            values.update({'submit_elec': 'na'}) 
        
        if tracking_id:
            tracking_id.write(values)
        
    def buy_insurance(self, picking, shipment):
        shipment_id = shipment.get('id')
        customs_items = shipment.get('customs_info').get('customs_items')
        insure_amount = 0
        for value in customs_items:
            if self.insurance_calculation == 'cost':
                product_id = self.env['product.product'].browse(int(value.get('description').split('-')[-1]))
                insure_amount += (product_id.standard_price * float(value.get('quantity'))) 
            else:
                insure_amount += float(value.get('value'))
        if insure_amount > 0:    
            purchased_shipment = easypost.Shipment.retrieve(shipment_id)
            purchased_shipment.insure(amount=insure_amount)
        else:
            raise UserError(_("Shipped items require a value grater then 0 to buy insurance."))