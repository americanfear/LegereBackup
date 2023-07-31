from odoo import api, fields, models, _

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    legere_customer_ID = fields.Char("Legere Customer ID", compute='_compute_customer', compute_sudo=True)
    legere_customer_name = fields.Char("Legere Customer Name", compute='_compute_customer', compute_sudo=True)

    @api.depends('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id')
    def _compute_customer(self):
        for record in self:
            record.legere_customer_ID = ''
            record.legere_customer_name = ''
            sale_id = record.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
            if sale_id:
                record.legere_customer_ID = sale_id.partner_id.legere_customer_ID
                record.legere_customer_name = sale_id.partner_id.name

    def action_set_progress(self):
        for record in self:
            record.state = 'progress'