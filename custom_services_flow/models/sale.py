from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_custom_service = fields.Boolean('Custom Service')

    #check to see if any order lines are custom services and marks SO as Custom Project accordingly
    @api.onchange('order_line')
    def onchange_order_lines_custom_service(self):
        for line in self.order_line:
            if line.product_id.is_custom == 1:
                self.is_custom_service = 1
                break
            else:
                self.is_custom_service = 0
    
    def _action_confirm(self):
        #inherit the function from sale.order _action_confirm to create global task for project not based on a service
        res = super(SaleOrder, self)._action_confirm()
        if self.is_custom_service:            
            project_id = self.company_id.custom_project_id
            if not project_id:
                raise ValidationError('Please Select Default Custom Service Project in Settings')

            # create project task for the sale order with
            if project_id:
                task_val = {
                    'name': f"""{self.name} - {self.client_order_ref or ""}""",
                    'project_id': int(project_id),
                    'sale_order_id': self.id,
                    'is_work_preparation': True,
                    'partner_id': self.partner_id.id,
                }
                self.env['project.task'].create(task_val)
        return res