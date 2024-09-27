from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    order_notes = fields.Text(string='Order Notes')

    def action_email_order_confirmation(self):
        for order in self:
            try:
                template = order.env.ref(
                    'legere_custom.mail_template_sale_confirmation',
                    raise_if_not_found=False
                )
                # _logger.info(f'>>>>>>>VALIDATE EMAIL: id:{order.id}, state:{order.state}, tracking:{order.carrier_tracking_ref}')
                if template:
                    # _logger.info('>>>>>>>VALIDATE SEND EMAIL')
                    template.send_mail(order.id, email_layout_xmlid='legere_custom.mail_notification_layout', force_send=True)
            except Exception as e:
                _logger.error("%s", str(e))

    def action_email_order_update(self):
        for order in self:
            try:
                template = order.env.ref(
                    'legere_custom.mail_template_update_sale_confirmation',
                    raise_if_not_found=False
                )
                # _logger.info(f'>>>>>>>VALIDATE EMAIL: id:{order.id}, state:{order.state}, tracking:{order.carrier_tracking_ref}')
                if template:
                    # _logger.info('>>>>>>>VALIDATE SEND EMAIL')
                    template.send_mail(order.id, email_layout_xmlid='legere_custom.mail_notification_layout', force_send=True)
            except Exception as e:
                _logger.error("%s", str(e))

    def write(self, vals):
        new_state = "state" in vals and vals["state"]
        new_non_olympia_orders = []
        for order in self:
            if order.state != new_state and new_state == "sale":
                olympia_product_orderlines = order.order_line.filtered(lambda x: x.product_id and x.product_id.categ_id.olympia_product)
                if not olympia_product_orderlines:
                    new_non_olympia_orders.append(order)
        super(SaleOrder, self).write(vals)
        # Loop through New Non-Olympia Orders and send each one an initial email
        for order in new_non_olympia_orders:
            order.action_email_order_confirmation()

    def legere_validate_dropship(self):
        for order in self:
            _logger.info(f'||||VALIDATE DROPSHIP: Sale order: {order}, picking_ids: {order.picking_ids}')
            for picking in order.picking_ids:
                # Only call validate if in the proper state
                # TODO: Handle case where it is in an unexpected state
                # TODO: Handle more than 1 dropship record
                _logger.info(f'||||VALIDATE DROPSHIP: picking: {picking}')
                if picking.state in ['confirmed', 'assigned'] and picking.picking_type_id.name == "Dropship":
                    _logger.info(f'||||VALIDATE DROPSHIP: button_validate')
                    try:
                        picking.action_put_in_pack()
                    except Exception:
                        _logger.info(f'||||VALIDATE DROPSHIP:Exception: {Exception}')
                    picking.button_validate()

    def legere_get_dropship(self):
        order = self
        dropships = []
        _logger.info(f'||||GET DROPSHIP: Sale order: {order}, picking_ids: {order.picking_ids}')
        for picking in order.picking_ids:
            _logger.info(f'||||GET DROPSHIP: picking: {picking}')
            if picking.picking_type_id.name == "Dropship":
                dropships.append(picking)
        return dropships