from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_work_preparation = fields.Boolean('Is Work Preparation', help='This is a work preparation project')

class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_work_preparation = fields.Boolean()
    mo_count = fields.Integer(compute='get_mo_count')
    purchase_order_count = fields.Integer("Number of Purchase Order Generated",
        compute='_compute_purchase_order_count', groups='purchase.group_purchase_user')

    #@api.depends('sale_order_id', 'sale_order_id.order_line.purchase_line_ids.order_id')
    def _compute_purchase_order_count(self):
        for record in self:
            record.purchase_order_count = len(record.sale_order_id._get_purchase_orders()) if record.sale_order_id else 0
     
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

    def action_view_purchase_orders(self):
        self.ensure_one()
        purchase_order_ids = self.sale_order_id._get_purchase_orders().ids
        action = {
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
        }
        if len(purchase_order_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': purchase_order_ids[0],
            })
        else:
            action.update({
                'name': _("Purchase Order generated from %s", self.sale_order_id.name),
                'domain': [('id', 'in', purchase_order_ids)],
                'view_mode': 'tree,form',
            })
        return action