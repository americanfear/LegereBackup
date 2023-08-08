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
        projects = []
        for record in self:
            for line in record.order_line.filtered(lambda x: x.product_id and x.product_id.is_custom):
                if not line.product_id.custom_project_id:
                    raise ValidationError(_('Please Select Default Custom Service Project On Product: %s.', line.product_id.name))
                
                task_name = record.name
                if record.client_order_ref:
                    task_name += ' - ' + record.client_order_ref
                multiple = record.order_line.filtered(lambda x: x.product_id.group_task and x.product_id.custom_project_id.id == line.product_id.custom_project_id.id and x.id != line.id)
                if multiple and line.product_id.group_task:
                    task_name += ' - Multiple Products'
                else:
                    task_name += ' - ' + line.product_id.name
                
                if not line.product_id.group_task or line.product_id.custom_project_id.name not in projects:
                    project_task_pool.create({
                        'name': task_name,
                        'project_id': line.product_id.custom_project_id.id,
                        'sale_order_id': record.id,
                        'is_work_preparation': True,
                        'partner_id': record.partner_id.id,
                    })
                    projects.append(line.product_id.custom_project_id.name)
        return res