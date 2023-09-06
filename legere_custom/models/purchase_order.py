from odoo import api, fields, models, _

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    po_bill_batch_id = fields.Many2one('po.bill.batch', string='Purchase Bill Batch')