from odoo import api, fields, models, _

class ProjectTask(models.Model):
    _inherit = "project.task"

    order_notes = fields.Text(string='Order Notes', related='sale_order_id.order_notes')