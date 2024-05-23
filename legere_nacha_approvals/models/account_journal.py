# coding: utf-8
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    legere_nacha_discretionary_data = fields.Char(help="This will be provided by your bank.",
                                                  string="Company Discretionary Data")
