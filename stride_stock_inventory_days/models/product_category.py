from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    def _get_default_no_of_days(self):
        company = self.env.company
        return company.average_no_of_days if company else 0

    average_no_of_days = fields.Float(string="Average Number of Days", default=_get_default_no_of_days,
                                            help="Enter the number of days you want to average to calculate days of inventory.")
