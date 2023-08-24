from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_stride_payment(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return ''

        move_ids = self.browse(active_ids)
        if len(move_ids.mapped('partner_id')) > 1:
            raise ValidationError(_('Please select records of same partner.'))
        if move_ids.filtered(lambda x: x.payment_state in ['paid', 'in_payment'] or x.state != 'posted' or x.move_type != 'out_invoice'):
            raise ValidationError(_('Please only select posted and unpaid invoices.'))
        form = self.env.ref('stride_payments.stride_invoice_payment_form', raise_if_not_found=False)
        payment_token = self.env['payment.token'].sudo().search([('partner_id', '=', move_ids.partner_id.id),
            ('provider_id.state', '!=', 'disabled')], limit=1)
        ctx = dict(
            default_invoice_ids=[(6, 0, move_ids.ids)],
            default_payment_method='token' if payment_token else 'card',
            default_payment_token_id=payment_token.id if payment_token else False,
            default_provider_id=payment_token.provider_id.id if payment_token else False,
            invoice_ids=move_ids.ids
        )
        return {
            'name': _('Stride Invoice Payment'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stride.invoice.payment',
            'views': [(form.id, 'form')],
            'view_id': form.id,
            'target': 'new',
            'context': ctx,
        }