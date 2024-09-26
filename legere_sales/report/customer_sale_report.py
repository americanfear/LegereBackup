from odoo import api, fields, models

class CustomerSaleReport(models.Model):
    _name = "customer.sale.report"
    _description = "Customer Sales Analysis Report"
    
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    # product = fields.Char(string='Product', readonly=True)
    last_order_date = fields.Date(string='Last Order Date', readonly=True)
    last_order_qty = fields.Float(string='Last Order Qty', readonly=True)
    last_order_price = fields.Float(string='Last Order Price', readonly=True)
    total_order_qty = fields.Float(string='LTV Qty', readonly=True)
    total_order_price = fields.Float(string='LTV Price', readonly=True)

    def action_view_report_lines(self):
        self.partner_id._compute_customer_sale_report_line()
        action = self.env['ir.actions.act_window']._for_xml_id('legere_sales.action_customer_sale_line_report')
        action['domain'] = [('id', 'in', self.partner_id.customer_sale_report_line_ids.filtered(lambda x: x.product_id == self.product_id).ids)]
        action['context'] = {}
        return action

class CustomerSaleReportLine(models.Model):
    _name = "customer.sale.report.line"
    _description = "Customer Sales Analysis Report Lines"
    _order = 'order_date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    order_number = fields.Char(string='Order Number', readonly=True)
    order_date = fields.Datetime(string='Order Date', readonly=True)
    # product = fields.Char(string='Product', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    order_qty = fields.Float(string='Qty Ordered', readonly=True)
    unit_price = fields.Float(string='Unit Price', readonly=True)
    total_price = fields.Float(string='Total', readonly=True)
