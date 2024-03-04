from odoo import api, fields, models

class CustomerSaleReport(models.Model):
    _name = "customer.sale.report"
    _description = "Customer Sales Analysis Report"
    
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True, ondelete='cascade')
    product = fields.Char('Product', readonly=True)
    last_order_date = fields.Date('Last Order Date', readonly=True)
    last_order_qty = fields.Float('Last Order Qty', readonly=True)
    last_order_price = fields.Float('Last Order Price', readonly=True)
    total_order_qty = fields.Float('LTV Qty', readonly=True)
    total_order_price = fields.Float('LTV Price', readonly=True)