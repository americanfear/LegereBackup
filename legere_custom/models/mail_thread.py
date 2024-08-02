from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_process(self, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None):
        _logger.info(f'||||MESSAGE:model: {model}')
        _logger.info(f'||||MESSAGE:message: {message}')
        _logger.info(f'||||MESSAGE:custom_values: {custom_values}')
        return self.super(model, message, custom_values, save_original, strip_attachments, thread_id)

