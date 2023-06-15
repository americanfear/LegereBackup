from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_work_preparation = fields.Boolean('Is Work Preparation', help='This is a work preparation project')

class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_work_preparation = fields.Boolean()
    mo_count = fields.Integer(compute='get_mo_count')
    
    def get_mo_count(self):
        for rec in self:
            if rec.sale_order_id:
                rec.mo_count = len(self.env['mrp.production'].search([('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id', '=', rec.sale_order_id.id)]))
            else:
                rec.mo_count = 0

    def filter_mo(self):
        action = self.env.ref('mrp.mrp_production_action').sudo().read()[0]
        action['domain'] = [('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id', '=', self.sale_order_id.id)]
        return action