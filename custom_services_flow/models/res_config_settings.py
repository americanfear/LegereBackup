from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    custom_project_id = fields.Many2one('project.project', string="Project for Custom Services")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    custom_project_id = fields.Many2one(string='Project for Custom Services', readonly=False, related='company_id.custom_project_id')