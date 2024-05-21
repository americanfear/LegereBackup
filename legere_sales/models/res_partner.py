from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.depends('sale_order_ids', 'sale_order_ids.state', 'sale_order_ids.partner_id', 'sale_order_ids.order_line')
    def _compute_customer_sale_report(self):
        legere_order_part_pool = self.env['legere.order.part']
        sale_order_line_pool = self.env['sale.order.line']
        for record in self:
            record.customer_sale_report_ids = False
            all_partners = self.with_context(active_test=False).search([('id', 'child_of', record.ids)])
            #Odoo sales orders
            sale_order_lines = sale_order_line_pool.search([('order_partner_id', 'in', all_partners.ids), ('state', 'in', ['sale', 'done'])])
            products = sale_order_lines.mapped('product_id')
            report_lines = []
            for product in products:
                last_sale_order_line = sale_order_line_pool.search([('order_partner_id', 'in', all_partners.ids), 
                    ('state', 'in', ['sale', 'done']),
                    ('product_id', '=', product.id)], order='date_order desc, id desc', limit=1)
                all_order_lines = sale_order_line_pool.search([('order_id', '=', last_sale_order_line.order_id.id),
                    ('product_id', '=', product.id)])
                report_lines.append(
                    (0, 0, {'partner_id': record.id,
                            'product': product.display_name,
                            'last_order_date': last_sale_order_line.order_id.date_order.date(),
                            'last_order_qty': sum(all_order_lines.mapped('product_uom_qty')),
                            'last_order_price': max(all_order_lines.mapped('price_unit')),
                            'total_order_qty': sum(sale_order_lines.filtered(lambda x: x.product_id == product).mapped('product_uom_qty')),
                            'total_order_price': sum(sale_order_lines.filtered(lambda x: x.product_id == product).mapped('price_unit')),
                            })
                        )

            #Legere sales orders
            all_partners = self.with_context(active_test=False).search([('id', 'child_of', record.ids)]).mapped('legere_customer_ID')
            legere_order_lines = legere_order_part_pool.search([('OrderID.LegereCustomerNumber', 'in', all_partners)])
            products = legere_order_lines.mapped('ProductNumber')
            for product in list(set(products)):
                last_legere_order_line = legere_order_part_pool.search([('OrderID.LegereCustomerNumber', 'in', all_partners), 
                    ('DateOrderEntered', '!=', False),
                    ('ProductNumber', '=', product)], order='DateOrderEntered desc, id desc', limit=1)
                report_lines.append(
                    (0, 0, {'partner_id': record.id,
                            'product': product,
                            'last_order_date': last_legere_order_line.OrderID.DateOrderEntered.date(),
                            'last_order_qty': last_legere_order_line.QtyOrdered,
                            'last_order_price': last_legere_order_line.UnitPrice,
                            'total_order_qty': sum(legere_order_lines.filtered(lambda x: x.ProductNumber == product).mapped('QtyOrdered')),
                            'total_order_price': sum(legere_order_lines.filtered(lambda x: x.ProductNumber == product).mapped('UnitPrice')),
                            })
                        )
            record.customer_sale_report_ids = report_lines

    licensed = fields.Boolean(string='Is Licensed')
    license_number = fields.Char(string='License Number')
    NPI_number = fields.Char(string='NPI Number')
    license_expiration_date = fields.Date(string='License Expiration Date')
    olympia_login = fields.Char(string='Olympia Login')
    customer_sale_report_ids = fields.One2many('customer.sale.report', 'partner_id', string='Customer Sale Report', compute='_compute_customer_sale_report', store=True, compute_sudo=True)

    def action_view_customer_sale_report(self):
        self._compute_customer_sale_report()
        action = self.env['ir.actions.act_window']._for_xml_id('legere_sales.action_customer_sale_report')
        action['domain'] = [('id', 'in', self.customer_sale_report_ids.ids)]
        action['context'] = {}
        return action