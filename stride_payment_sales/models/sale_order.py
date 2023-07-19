from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.invoice_lines', 'order_line.invoice_lines.move_id.amount_residual', 'order_line.invoice_lines.move_id.amount_total', 'transaction_ids', 'transaction_ids.state')
    def _compute_amount_payment_due(self):
        for record in self:
            amount_due = record.amount_total
            for transaction in record.transaction_ids.filtered(lambda x: not x.invoice_ids and x.state not in ['cancel', 'error']):
                amount_due -= transaction.amount
            invoices = record.order_line.invoice_lines.move_id.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund'))
            for invoice in invoices:
                if invoice.move_type == 'out_invoice':
                    amount_due -= (invoice.amount_total - invoice.amount_residual)
                elif invoice.move_type == 'out_refund':
                    amount_due += (invoice.amount_total - invoice.amount_residual)
            record.amount_payment_due = amount_due

    amount_payment_due = fields.Monetary(string='Amount Payment Due', compute='_compute_amount_payment_due', store=True)

    def action_stride_sale_payment(self):
        form = self.env.ref('stride_payment_sales.stride_sale_payment_form', raise_if_not_found=True)
        self._cr.execute('delete from stride_sale_payment_line')
        self._cr.execute('delete from stride_sale_payment')
        wiz = self.env['stride.sale.payment'].create({
            'sale_order_id': self.id,
            'amount': self.amount_payment_due,
            'authorize_name_on_account': self.partner_invoice_id.name,
            'payment_method': 'card',
            'company_id': self.company_id.id,
            'send_receipt': False
        })
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stride.sale.payment',
            'views': [(form.id, 'form')],
            'view_id': form.id,
            'target': 'new',
            'res_id': wiz.id,
        }

    def action_view_payment_transactions(self):
        action = self.env['ir.actions.act_window']._for_xml_id('payment.action_payment_transaction')

        if len(self.transaction_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.transaction_ids.id
            action['views'] = []
        else:
            action['domain'] = [('id', 'in', self.transaction_ids.ids)]

        return action