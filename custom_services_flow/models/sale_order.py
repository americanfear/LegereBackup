from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_custom_service = fields.Boolean('Custom Service')

    @api.onchange('order_line')
    def onchange_order_lines_custom_service(self):
        self.is_custom_service = True if self.order_line.filtered(lambda x: x.product_id and x.product_id.is_custom) else False

    def _action_confirm(self):
        res = super(SaleOrder, self)._action_confirm()
        project_task_pool = self.env['project.task'].sudo()
        for record in self:
            for line in record.order_line.filtered(lambda x: x.product_id and x.product_id.is_custom):
                if not line.product_id.custom_project_id:
                    raise ValidationError(_('Please Select Default Custom Service Project On Product: %s.', line.product_id.name))

                project_task_pool.create({
                    'name': f"""{record.name} - {record.client_order_ref or ""}""",
                    'project_id': line.product_id.custom_project_id.id,
                    'sale_order_id': record.id,
                    'is_work_preparation': True,
                    'partner_id': record.partner_id.id,
                })
        return res