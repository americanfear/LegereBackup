from odoo import api, fields, models, _

class ProjectTask(models.Model):
    _inherit = "project.task"

    customer_ID = fields.Integer(string='Customer ID', related='partner_id.id')