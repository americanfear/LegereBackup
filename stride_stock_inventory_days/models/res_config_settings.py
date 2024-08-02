from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    average_no_of_days = fields.Float(related="company_id.average_no_of_days",
                                            readonly=False, string="Average Number of Days",
                                            help="Enter the number of days you want to average to calculate days of inventory.")
