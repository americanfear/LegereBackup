from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    payment_term_id = fields.Many2one('account.payment.term', related='sale_id.payment_term_id', string='Payment Term', store=True)