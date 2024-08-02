from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    order_notes = fields.Text(string='Order Notes', related='sale_id.order_notes')

    def action_email_tracking_info(self):
        for record in self:
            if (
                    record.carrier_tracking_ref != False and
                    (record.sale_id.partner_invoice_id.email or record.sale_id.partner_id.email) and
                    record.picking_type_id.name in ["Dropship", "Delivery Orders"]
            ):
                try:
                    template = record.env.ref(
                        'legere_custom.email_template_order_tracking',
                        raise_if_not_found=False
                    )
                    # _logger.info(f'>>>>>>>VALIDATE EMAIL: id:{record.id}, state:{record.state}, tracking:{record.carrier_tracking_ref}')
                    if template:
                        test_only = False
                        if test_only:
                            email_to = record.sale_id.partner_invoice_id.email or record.sale_id.partner_id.email
                            values = template.generate_email(
                                record.id,
                                ['subject', 'body_html',
                                 'email_from',
                                 'email_cc', 'email_to', 'partner_to', 'reply_to',
                                 'auto_delete', 'scheduled_date']
                            )
                            body = f"""
                            <b>Email To</b>: {email_to}<br/>
                            <b>Subject</b>: {values['subject'] if "subject" in values else "NO subject"}<br/>
                            {values['body_html'] if "body_html" in values else "NO body_html"}
                            """
                            record.message_post(body=body)
                        # else:
                        if not test_only:
                            # template.send_mail(record.id, email_layout_xmlid='legere_custom.mail_notification_layout',
                            #                    force_send=True)
                            record.with_context(force_send=True).message_post_with_template(
                                template.id,
                                email_layout_xmlid='legere_custom.mail_notification_layout'
                            )
                        # _logger.info('>>>>>>>VALIDATE SEND EMAIL')
                except Exception as e:
                    _logger.error("%s", str(e))

    def button_validate(self):
        res = super().button_validate()
        self.action_email_tracking_info()
        return res
