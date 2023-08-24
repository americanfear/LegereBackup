from odoo import api, fields, models, _

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    order_notes = fields.Text(string='Order Notes', compute="_compute_order_notes",
        groups='sales_team.group_sale_salesman')

    @api.depends('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id')
    def _compute_order_notes(self):
        for production in self:
            production.order_notes = ''
            if production.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id:
                production.order_notes = production.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id[0].order_notes or ''