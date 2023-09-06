from odoo import api, fields, models, _

class PoBillBatchShippingCost(models.Model):
    _name = "po.bill.batch.shipping.cost"
    _description = "Purchase Bill Batch Shipping Cost"

    name = fields.Char(string='Shipping Item', required=True)
    amount = fields.Monetary(string='Cost')
    currency_id = fields.Many2one('res.currency', related='po_bill_batch_id.currency_id', string='Currency')
    po_bill_batch_id = fields.Many2one('po.bill.batch', string='Purchase Bill Batch', ondelete="cascade")

class PoBillBatchMissingOrder(models.Model):
    _name = "po.bill.batch.missing.order"
    _description = "Purchase Bill Batch Missing Order"

    name = fields.Text(string='Order Details')
    po_bill_batch_id = fields.Many2one('po.bill.batch', string='Purchase Bill Batch', ondelete="cascade")

class PoBillBatch(models.Model):
    _name = "po.bill.batch"
    _description = "Purchase Bill Batch"

    @api.depends('purchase_order_ids', 'purchase_order_ids.amount_total')
    def _compute_purchase_order_amount(self):
        for record in self:
            record.purchase_order_amount = sum(record.purchase_order_ids.mapped('amount_total')) if record.purchase_order_ids else 0.0

    @api.depends('shipping_cost_ids', 'shipping_cost_ids.amount')
    def _compute_shipping_cost(self):
        for record in self:
            record.shipping_cost = sum(record.shipping_cost_ids.mapped('amount')) if record.shipping_cost_ids else 0.0

    @api.depends('purchase_order_ids', 'purchase_order_ids.amount_total', 'shipping_cost_ids', 'shipping_cost_ids.amount')
    def _compute_amount_total(self):
        for record in self:
            purchase_order_amount = sum(record.purchase_order_ids.mapped('amount_total')) if record.purchase_order_ids else 0.0
            shipping_cost = sum(record.shipping_cost_ids.mapped('amount')) if record.shipping_cost_ids else 0.0
            record.amount_total = (purchase_order_amount + shipping_cost)

    name = fields.Char(
        string="Batch Reference",
        required=True, copy=False, readonly=True,
        index='trigram',
        default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    purchase_order_ids = fields.One2many('purchase.order', 'po_bill_batch_id', string='Purchase Order')
    missing_order_ids = fields.One2many('po.bill.batch.missing.order', 'po_bill_batch_id', string='Missing Orders')
    shipping_cost_ids = fields.One2many('po.bill.batch.shipping.cost', 'po_bill_batch_id', string="Shipping Costs")
    purchase_order_amount = fields.Monetary(string='Purchase Order Amount', compute='_compute_purchase_order_amount')
    shipping_cost = fields.Monetary(string='Shipping Cost', compute='_compute_shipping_cost')
    amount_total = fields.Monetary(string='Amount Total', compute="_compute_amount_total")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'po.bill.batch') or _("New")
        return super(PoBillBatch, self).create(vals_list)