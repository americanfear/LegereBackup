from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    average_no_of_days = fields.Float(string="Average Number of Days", help="Enter the number of days you want to average to calculate days of inventory.")
