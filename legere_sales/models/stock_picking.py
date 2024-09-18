from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    payment_term_id = fields.Many2one('account.payment.term', related='sale_id.payment_term_id', string='Payment Term', store=True)

    def action_view_sale_order(self):
        action = self.env['ir.actions.actions']._for_xml_id('sale.action_orders')
        form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
        if 'views' in action:
            action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
        else:
            action['views'] = form_view
        action['res_id'] = self.sale_id.id
        return action 