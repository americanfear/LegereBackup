from odoo import api, fields, models, _
from pypdf import PdfReader
import io
import re
import logging

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_process(self, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None):
        # _logger.info(f'||||MESSAGE:model: {model}')
        # _logger.info(f'||||MESSAGE:message: {message}')
        # _logger.info(f'||||MESSAGE:custom_values: {custom_values}')
        return super(MailThread, self).message_process(model, message, custom_values, save_original, strip_attachments, thread_id)
        # return self.super(model, message, custom_values, save_original, strip_attachments, thread_id)

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
        routes = super(MailThread, self).message_route(message, message_dict, model, thread_id, custom_values)
        new_routes = []
        if not routes or len(routes) == 0:
            # _logger.info(f'||||MESSAGE:msg_dict: {message_dict}')
            if 'attachments' in message_dict:
                reg = r'S\d{5,6}'
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
                            po_text_block = ""
                            # Look at text between PO Number and Terms
                            split_text_on_po = text.split('P.O. No.')
                            if len(split_text_on_po) > 1:
                                split_text_on_terms = split_text_on_po[1].split('Terms')
                                if len(split_text_on_terms) > 1:
                                    po_text_block = split_text_on_terms[0]
                            if po_text_block:
                                po_numbers = re.findall(reg, po_text_block)
                                for po in po_numbers:
                                    _logger.info(f'||||MESSAGE:PDF:Sales order: {po}')
                                    # so = self.env['sale.order'].search([('name', '=', po)])
                                    # if so:
                                    #     email_from = message_dict['email_from']
                                    #     user_id = self._mail_find_user_for_gateway(email_from).id or self._uid
                                    #     new_routes.append(('sale.order', thread_id, custom_values, user_id, None))

                            _logger.info(f'||||MESSAGE:PDF:number_of_pages: {number_of_pages}')
                            _logger.info(f'||||MESSAGE:PDF:text: {text}')
                        except Exception:
                            _logger.info(f'||||MESSAGE:PDF:Exception: {Exception}')
        return new_routes if new_routes else routes
        # return: list of routes [(model, thread_id, custom_values, user_id, alias)]
