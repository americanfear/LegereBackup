from odoo import api, fields, models, _

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    product_category_id = fields.Many2one('product.category', related='product_id.categ_id', string='Product Category', store=True)
    sales_order_number = fields.Char(string='Sales Order Number', compute='_compute_sales_order_data', store=True)
    sales_order_date = fields.Datetime(string='Sales Order Date', compute='_compute_sales_order_data', store=True)
    invoice_number = fields.Char(string='Invoice Number', related='move_id.name', store=True)
    invoice_date = fields.Date(string='Invoice Date', related='move_id.date', store=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson', related='move_id.invoice_user_id', store=True)
    customer_id = fields.Many2one('res.partner', string='Customer', related='move_id.partner_id', store=True)
    order_line_total_amount = fields.Monetary(string='Order Line Total', compute='_compute_sales_order_data', store=True)
    order_total_amount = fields.Monetary(string='Order Total', compute='_compute_sales_order_data', store=True)
    shipping_amount = fields.Monetary(string='Shipping Amount', compute='_compute_sales_order_data', store=True)
    product_internal_ref = fields.Char(string='Product internal ref', related='product_id.default_code', store=True)
    cogs_amount = fields.Monetary(string='COGS Amount', compute='_compute_invoice_data', store=True)

    @api.depends('sale_line_ids', 'sale_line_ids.order_id.date_order', 'sale_line_ids.price_total', 'sale_line_ids.order_id.amount_total')
    def _compute_sales_order_data(self):
        for record in self:
            record.sales_order_number = ''
            record.sales_order_date = False
            record.order_line_total_amount = sum(record.sale_line_ids.mapped('price_total'))
            record.shipping_amount = sum(record.sale_line_ids.filtered(lambda x: x.is_delivery).mapped('price_total'))
            record.order_total_amount = sum(record.sale_line_ids.mapped('order_id.amount_total'))
            orders = record.sale_line_ids.mapped('order_id')
            if orders:
                record.sales_order_number = orders[0].name
                record.sales_order_date = orders[0].date_order

    @api.depends('move_id', 'move_id.invoice_line_ids', 'move_id.invoice_line_ids.price_total')
    def _compute_invoice_data(self):
        for record in self:
            record.cogs_amount = sum(record.move_id.invoice_line_ids.filtered(lambda x: x.account_id.account_type == 'expense_direct_cost').mapped('price_total'))