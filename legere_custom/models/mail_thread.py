from odoo import api, fields, models, _
from pypdf import PdfReader
import io
import re
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # @api.model
    # def message_process(self, model, message, custom_values=None,
    #                     save_original=False, strip_attachments=False,
    #                     thread_id=None):
    #     # _logger.info(f'||||MESSAGE:model: {model}')
    #     # _logger.info(f'||||MESSAGE:message: {message}')
    #     # _logger.info(f'||||MESSAGE:custom_values: {custom_values}')
    #     return super(MailThread, self).message_process(model, message, custom_values, save_original, strip_attachments, thread_id)
    #     # return self.super(model, message, custom_values, save_original, strip_attachments, thread_id)

    # @api.model
    # def message_parse(self, message, save_original=False):
    #     msg_dict = super(MailThread, self).message_parse(message, save_original)
    #     _logger.info(f'||||MESSAGE:msg_dict: {msg_dict}')
    #     if 'attachments' in msg_dict:
    #         for attachment in msg_dict['attachments']:
    #             _logger.info(f'||||MESSAGE:attachment: {attachment}')
    #             if attachment[0].endswith('.pdf'):
    #                 try:
    #                     binary_data = io.BytesIO(attachment[1])
    #                     reader = PdfReader(binary_data)
    #                     number_of_pages = len(reader.pages)
    #                     page = reader.pages[0]
    #                     text = page.extract_text()
    #                     _logger.info(f'||||MESSAGE:PDF:number_of_pages: {number_of_pages}')
    #                     _logger.info(f'||||MESSAGE:PDF:text: {text}')
    #                 except Exception:
    #                     _logger.info(f'||||MESSAGE:PDF:Exception: {Exception}')
    #     return msg_dict

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        _logger.info(f'||||MESSAGE: model: {model}')
        routes = []
        if model != 'email.incoming':
            routes = super(MailThread, self).message_route(message, message_dict, model, thread_id, custom_values)
        _logger.info(f'||||MESSAGE: routes: {routes}')
        _logger.info(f'||||MESSAGE:Email: message_dict: {message_dict}')
        # Look for email.incoming Class to trigger special parsing
        # filtered_routes = []
        # for route in routes:
        #     if route[0] != 'email.incoming':
        #         filtered_routes.append(route)
        # routes = filtered_routes

        # If Shipping info, search for UPS Ship Notification, Tracking Number, Scheduled Delivery,
        # If PDF, can try to find Olympia invoice info, else attach to Incoming Email Task
        new_routes = []
        if not routes or len(routes) == 0:
            proj = self.env['project.project'].search([('name', '=', 'Handle Incoming Email')])
            if not proj:
                proj = self.env['project.project'].create({
                    'name': 'Handle Incoming Email',
                })
                _logger.info(f'||||MESSAGE: Create project "Handle Incoming Email": {proj}')
            # PLAN:
            #   If UPS Tracking info found
            #       Try to extract Tracking Number, Delivery Date, and Customer Name
            #       Try to look up Sales Order by Customer Name and approx. Order Date (from Shipping Date)
            #       If 1 and only 1 Sales Order, then go to Dropship, Attach email, add tracking, send tracking email
            #       Else if 0 or more found, create a new Task and attach email to that
            # Prep email for easier regex searching
            message_body = message = re.sub('\n', ' || ', str(message))
            message_body = message = re.sub('=3D', '=', message_body)
            message_body = message = re.sub(r'=\s* \|\| \s*', '', message_body)
            message_body = message = re.sub(r' \|\| ', '', message_body)
            tracking_regex = r'Tracking Number'
            tracking_href_regex = r'href="(https://www.ups.com/track?[^"]+)"'
            tracknum_regex = r'tracknum=(\w+)&'
            # shipping_cust_regex = r'Reference Number 1:(</[^>]+>|<\w+[^>]+>)+LEG:([^<]+)<'
            cust_regex = r'LEG:([\w ]+)'
            shipping_date_regex = r'Scheduled Delivery:(</[^>]+>|<\w+[^>]+>)+([^<]+)<'
            email_from = message_dict['email_from']
            user_id = self._mail_find_user_for_gateway(email_from).id or self._uid

            # If Tracking Info present try to handle it as a Tracking email
            if re.findall(tracking_regex, message_body):
                tracking_href = list(set(re.findall(tracking_href_regex, message_body)))
                tracknum = list(set(re.findall(tracknum_regex, message_body)))
                customers = list(set(re.findall(cust_regex, message_body)))
                del_date = list(set(re.findall(shipping_date_regex, message_body)))
                _logger.info(f'||||MESSAGE:Email: Found: tracknum:{tracknum}, tracking_href:{tracking_href}, cust:{customers}, del_date:{del_date}')
                if len(tracknum) == 1 and len(tracking_href) == 1 and len(customers) == 1 and len(del_date) == 1:
                    _logger.info(f'||||MESSAGE:Email: Find 1: tracknum:{tracknum[0]}, tracking_href:{tracking_href[0]}, cust:{customers[0]}, del_date:{del_date[0]}')
                    delivery_date = datetime.strptime(del_date[0][1], "%m/%d/%Y")
                    est_order_day = delivery_date - timedelta(days=5)
                    _logger.info(f'||||MESSAGE:Email: Found: delivery_date:{delivery_date}, est_order_day:{est_order_day}')
                    # Search for a Sales Order for the customer around the date specified
                    sos = self.env['sale.order'].search([
                        ('partner_id.name', 'ilike', customers[0]),
                        ('date_order', '>', est_order_day),
                        ('date_order', '<', delivery_date)
                    ])
                    _logger.info(f'||||MESSAGE:sale orders found: sos:{sos}')
                    if len(sos) == 1:
                        so = sos[0]
                        dropships = so.legere_get_dropship()
                        _logger.info(f'||||MESSAGE:Dropship: dropships: {dropships}')
                        if len(dropships) == 1:
                            dropship = dropships[0]
                            _logger.info(f'||||MESSAGE:Dropship: {dropship}')
                            # Continue to set tracking num
                            issue = dropship.legere_update_tracking_info(tracknum[0], tracking_href[0])
                            if not issue:
                                # Attach email to the Dropship record
                                new_routes.append(('stock.picking', dropship.id, custom_values, user_id, None))
                                _logger.info(f'||||MESSAGE:Stock Picking:dropship found: {dropship}, user_id: {user_id}')
                                pass
                            else:
                                # Add Task to follow up on email
                                pass
                        else:
                            # Add Task to follow up on email
                            # Or, attach to SO and add activity to SO to follow up?
                            _logger.info(f'||||MESSAGE:1 Dropship not found: {dropships}')
                            pass
                        # so.legere_validate_dropship()
                        # new_routes.append(('sale.order', so.id, custom_values, user_id, None))
                        _logger.info(f'||||MESSAGE:Sale Order:so found: {so}')
                if not new_routes:
                    # Get Project
                    cust = self.env['res.partner'].search([('name', 'ilike', customers[0])]) if customers and len(customers) == 1 else None
                    if proj:
                        new_task = self.env['project.task'].create({
                            'name': f'Tracking Email',
                            'project_id': proj.id,
                            'partner_id': cust.id if cust and len(cust) == 1 else False,
                        })
                        new_routes.append(('project.task', new_task.id, custom_values, user_id, None))
                    else:
                        _logger.error('||||MESSAGE:PDF:Unable to find or create "Handle Incoming Email" project')
            #   Else If PDF, search for PO number
            #       If 1 or more POs,
            #           attach mail to them
            #           Trigger validate on dropship
            #       If 0 POs,
            #           Search for customer PO near date on PDF for an amount near the PDF
            #           If exactly 1 match found, attach it and trigger validate on dropship
            #           Else, create Task for Incoming Email and attach it to that
            elif 'attachments' in message_dict:
                po_regex = r'S\d{5,6}'
                date_regex = r'\|\s*Date\s*\|\s*(\d\d?/\d\d?/\d\d\d\d)'
                cust_regex = r'Bill To\s*\|\s*([a-zA-Z\s]+)\|'
                invoice_regex = r'Invoice\s*#\s*\|\s*(\d+)\s*\|'
                for attachment in message_dict['attachments']:
                    # _logger.info(f'||||MESSAGE:attachment: {attachment}')
                    if attachment[0].endswith('.pdf'):
                        try:
                            binary_data = io.BytesIO(attachment[1])
                            reader = PdfReader(binary_data)
                            number_of_pages = len(reader.pages)
                            page = reader.pages[0]
                            text = page.extract_text()
                            # Search for P.O. No. (may have none, 1, or more than 1)
                            po_text_block = re.sub('\n', ' | ', text)
                            _logger.info(f'||||MESSAGE:PDF:po_text_block: {po_text_block}')
                            # Use a set to make sure they are all unique Sales Orders
                            po_numbers = set(re.findall(po_regex, po_text_block))
                            cust_name = ""
                            _logger.info(f'||||MESSAGE:PDF:po_numbers: {po_numbers}')
                            if len(po_numbers) > 0:
                                for po in po_numbers:
                                    _logger.info(f'||||MESSAGE:PDF:Sales order: {po}')
                                    so = self.env['sale.order'].search([('name', '=', po)])
                                    if so:
                                        so.legere_validate_dropship()
                                        new_routes.append(('sale.order', so.id, custom_values, user_id, None))
                                        _logger.info(f'||||MESSAGE:Sale Order:so: {so}, user_id: {user_id}')

                            # If no valid sales order numbers in PDF, try to look it up by customer and date
                            if len(new_routes) == 0:
                                dates = re.findall(date_regex, po_text_block)
                                customers = re.findall(cust_regex, po_text_block)
                                if len(customers) == 1:
                                    cust_name = customers[0].strip()
                                if len(dates) == 1 and len(customers) == 1:
                                    order_date = datetime.strptime(dates[0], "%m/%d/%Y")
                                    prev_day = order_date - timedelta(days=1)
                                    next_day = order_date + timedelta(days=1)
                                    # Search for a Sales Order for the customer around the date specified
                                    sos = self.env['sale.order'].search([
                                        ('partner_id.name', '=', cust_name),
                                        ('date_order', '>', prev_day),
                                        ('date_order', '<', next_day)
                                    ])
                                    if len(sos) == 1:
                                        so = sos[0]
                                        so.legere_validate_dropship()
                                        new_routes.append(('sale.order', so.id, custom_values, user_id, None))
                                        _logger.info(f'||||MESSAGE:Sale Order:so found: {so}, user_id: {user_id}')

                                _logger.info(f'||||MESSAGE:dates: {dates}')
                                _logger.info(f'||||MESSAGE:cust: {customers}')

                            # If no routes yet identified, create a Task to manually handle
                            if len(new_routes) == 0:
                                inv_nums = re.findall(invoice_regex, po_text_block)
                                invoice_num = inv_nums[0] if inv_nums else ''
                                customers = self.env['res.partner'].search([('name', '=', cust_name)]) if cust_name else None
                                if proj:
                                    new_task = self.env['project.task'].create({
                                        'name': f'Invoice #{invoice_num}' if invoice_num else 'Other Email',
                                        'project_id': proj.id,
                                        'partner_id': customers.id if customers else False,
                                    })
                                    new_routes.append(('project.task', new_task.id, custom_values, user_id, None))
                                else:
                                    _logger.error('||||MESSAGE:PDF:Unable to find "Handle Incoming Email" project')
                            _logger.info(f'||||MESSAGE:PDF:number_of_pages: {number_of_pages}')
                        except Exception:
                            _logger.info(f'||||MESSAGE:PDF:Exception: {Exception}')

        _logger.info(f'||||MESSAGE:PDF:new_routes: {new_routes}')
        return new_routes if new_routes else routes
        # return: list of routes [(model, thread_id, custom_values, user_id, alias)]
