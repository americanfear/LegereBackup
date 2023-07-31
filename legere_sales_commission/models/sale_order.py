from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_new_customer = fields.Boolean(string='New Customer', copy=False)

    def _prepare_invoice(self):
        values = super(SaleOrder, self)._prepare_invoice()
        values.update({'is_new_customer': self.is_new_customer})
        return values

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_new_product = fields.Boolean(string='New Product', copy=False)

    def _prepare_invoice_line(self, **optional_values):
        values = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        values.update({'is_new_product': self.is_new_product})
        return values