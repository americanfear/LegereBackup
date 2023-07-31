from odoo import api, fields, models, _

class ProjectTask(models.Model):
    _inherit = "project.task"

    customer_ID = fields.Integer(string='Customer ID', related='partner_id.id')
    olympia_login = fields.Char(string='Olympia Login', related='partner_id.olympia_login')