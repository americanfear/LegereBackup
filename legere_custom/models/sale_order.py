from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    order_notes = fields.Text(string='Order Notes')

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
