from odoo import models, fields, api,_

class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    auto_confirm_mo = fields.Boolean(string='Auto Confirm MO')

class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_work_preparation = fields.Boolean('Is Work Preparation', help='This is a work preparation project')
    filter_mo_po_based_product = fields.Boolean('Filter MO or PO Based On Product')

class ProjectTask(models.Model):
    _inherit = 'project.task'

    def write(self, vals):
        rec = super(ProjectTask, self).write(vals)
        if vals.get('stage_id'):
            for record in self:
                stage = self.env['project.task.type'].sudo().browse(vals.get('stage_id'))
                if record.sale_order_id and stage.auto_confirm_mo:
                    if record.project_id.filter_mo_po_based_product:
                        production_ids = self.env['mrp.production'].sudo().search([('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id', '=', record.sale_order_id.id)]).filtered(lambda x: x.product_id.id in record.product_ids.ids)
                    else:
                        production_ids = self.env['mrp.production'].sudo().search([('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id', '=', record.sale_order_id.id)])
                    production_ids.filtered(lambda x: x.state == 'draft').sudo().action_confirm()
        return rec
    
    is_work_preparation = fields.Boolean()
    mo_count = fields.Integer(compute='get_mo_count')
    purchase_order_count = fields.Integer("Number of Purchase Order Generated",
        compute='_compute_purchase_order_count', groups='purchase.group_purchase_user')
    product_ids = fields.Many2many('product.product', string='Products')

    #@api.depends('sale_order_id', 'sale_order_id.order_line.purchase_line_ids.order_id')
    def _compute_purchase_order_count(self):
        for record in self:
            if record.project_id.filter_mo_po_based_product:
                record.purchase_order_count = len(record.sale_order_id._get_purchase_orders().filtered(lambda x: x.order_line.product_id.id in record.product_ids.ids))
            else:
                record.purchase_order_count = len(record.sale_order_id._get_purchase_orders()) if record.sale_order_id else 0
     
    def get_mo_count(self):
        for rec in self:
            if rec.sale_order_id:
                if rec.project_id.filter_mo_po_based_product:
                    rec.mo_count = len(self.env['mrp.production'].search([('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id', '=', rec.sale_order_id.id)]).filtered(lambda x: x.product_id.id in rec.product_ids.ids))
                else:
                    rec.mo_count = len(self.env['mrp.production'].search([('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id', '=', rec.sale_order_id.id)]))
            else:
                rec.mo_count = 0

    def filter_mo(self):
        action = self.env.ref('mrp.mrp_production_action').sudo().read()[0]
        production_ids = self.env['mrp.production'].search([('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id', '=', self.sale_order_id.id)]).filtered(lambda x: x.product_id.id in self.product_ids.ids)
        if self.project_id.filter_mo_po_based_product:
            action['domain'] = [('id', 'in', production_ids.ids)]
        else:    
            action['domain'] = [('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id', '=', self.sale_order_id.id)]
        return action

    def action_view_purchase_orders(self):
        self.ensure_one()
        if self.project_id.filter_mo_po_based_product:
            purchase_order_ids = self.sale_order_id._get_purchase_orders().filtered(lambda x: x.order_line.product_id.id in self.product_ids.ids).ids
        else:
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