from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    legere_customer_ID = fields.Char(string='Legere Customer ID')
    total_legere_invoiced = fields.Monetary(compute='_invoice_legere_total', string="Total Legere Invoiced",
        groups='account.group_account_invoice')
    total_legere_ordered = fields.Monetary(compute='_order_legere_total', string="Total Legere Ordered",
        groups='sales_team.group_sale_salesman')

    def _invoice_legere_total(self):
        for record in self:
            all_partner_ids = self.with_context(active_test=False).search([('id', 'child_of', record.ids)]).mapped('legere_customer_ID')
            record.total_legere_invoiced = sum(self.env['legere.invoice'].search([('CustomerNumber', 'in', all_partner_ids)]).mapped('Subtotal'))

    def _order_legere_total(self):
        for record in self:
            all_partner_ids = self.with_context(active_test=False).search([('id', 'child_of', record.ids)]).mapped('legere_customer_ID')
            record.total_legere_ordered = sum(self.env['legere.order'].search([('LegereCustomerNumber', 'in', all_partner_ids)]).mapped('Subtotal'))

    def action_view_partner_legere_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("legere_legacy.action_legere_invoice")
        all_partner_ids = self.with_context(active_test=False).search([('id', 'child_of', self.ids)]).mapped('legere_customer_ID')
        action['domain'] = [
            ('CustomerNumber', 'in', all_partner_ids)
        ]
        return action

    def action_view_partner_legere_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("legere_legacy.action_legere_order")
        all_partner_ids = self.with_context(active_test=False).search([('id', 'child_of', self.ids)]).mapped('legere_customer_ID')
        action['domain'] = [
            ('LegereCustomerNumber', 'in', all_partner_ids)
        ]
        return action