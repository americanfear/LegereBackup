from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    is_new_customer = fields.Boolean(string='New Customer', copy=True)
    commission_lines = fields.One2many('sale.commission.line', 'invoice_id', string='Sale Commission Lines', readonly=True)

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        for record in self.filtered(lambda x: x.move_type in ['out_invoice', 'out_refund'] and x.invoice_user_id):
            record.create_commission_lines()
        return res

    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        for record in self.filtered(lambda x: x.commission_lines):
            if record.commission_lines.filtered(lambda x: x.sale_commission_id and x.sale_commission_id.paid):
                raise ValidationError(_('This invoice is linked with commission lines that are already paid.'))
            record.commission_lines.unlink()
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for record in self.filtered(lambda x: x.commission_lines):
            if record.commission_lines.filtered(lambda x: x.sale_commission_id and x.sale_commission_id.paid):
                raise ValidationError(_('This invoice is linked with commission lines that are already paid.'))
            record.commission_lines.unlink()
        return res

    def unlink(self):
        for record in self.filtered(lambda x: x.commission_lines):
            if record.commission_lines.filtered(lambda x: x.sale_commission_id and x.sale_commission_id.paid):
                raise ValidationError(_('This invoice is linked with commission lines that are already paid.'))
            record.commission_lines.unlink()
        return super(AccountMove, self).unlink()

    def create_commission_lines(self):
        sale_commission_line_pool = self.env['sale.commission.line']
        for record in self:
            sale_commission = self.env['sale.commission'].search([('user_id', '=', record.invoice_user_id.id),
                ('from_date', '>=', fields.Date.today()),
                ('to_date', '<=', fields.Date.today()),
                ('company_id', '=', record.company_id.id),
                ('paid', '=', False)], limit=1)
            commission_ids = self.env['commission.commission'].search([('active', '=', True),
                ('use_for_manager', '=', False)]).filtered(lambda x: record.invoice_user_id.id in x.user_ids.ids)
            for commission in commission_ids:
                for commission_rule in commission.commission_rule_ids:
                    #TODO: We will want to exclude shipping and ensure taxes are not included in these values as they don't pay commissions on those items.
                    if commission_rule.commission_type == 'new_customer' and commission_rule.commission_per > 0.0 and record.is_new_customer:
                        commission_amount = (record.amount_total * commission_rule.commission_per) / 100
                        commission_amount = commission_amount if record.move_type == 'out_invoice' else -commission_amount
                        sale_commission_line_pool.create({
                            'invoice_id': record.id,
                            'user_id': record.invoice_user_id.id,
                            'date': fields.Date.today(),
                            'company_id': record.company_id.id,
                            'commission_id': commission.id,
                            'commission_rule_id': commission_rule.id,
                            'commission_type': commission_rule.commission_type,
                            'amount': commission_amount,
                            'sub_total': record.amount_total if record.move_type == 'out_invoice' else -record.amount_total,
                            'sale_commission_id': sale_commission and sale_commission.id or False,
                        })
                    elif commission_rule.commission_type == 'new_product' and commission_rule.commission_per > 0.0 and record.invoice_line_ids.filtered(lambda x: x.is_new_product) and not record.is_new_customer:
                        amount_total = sum(record.invoice_line_ids.filtered(lambda x: x.is_new_product).mapped('price_total'))
                        commission_amount = (amount_total * commission_rule.commission_per) / 100
                        commission_amount = commission_amount if record.move_type == 'out_invoice' else -commission_amount
                        sale_commission_line_pool.create({
                            'invoice_id': record.id,
                            'user_id': record.invoice_user_id.id,
                            'date': fields.Date.today(),
                            'commission_id': commission.id,
                            'commission_rule_id': commission_rule.id,
                            'company_id': record.company_id.id,
                            'commission_type': commission_rule.commission_type,
                            'amount': commission_amount,
                            'sub_total': amount_total if record.move_type == 'out_invoice' else -amount_total,
                            'sale_commission_id': sale_commission and sale_commission.id or False,
                        })
                    elif commission_rule.commission_type == 'adjusted_sale_value_fixed' and not record.is_new_customer and commission_rule.commission_per > 0.0:
                        amount_total = sum(record.invoice_line_ids.filtered(lambda x: not x.is_new_product 
                            and x.product_id 
                            and x.product_id.categ_id.id in commission_rule.product_category_ids.ids
                            and x.discount >= commission_rule.min_discount
                            and x.discount <= commission_rule.max_discount).mapped('price_total'))
                        if amount_total > 0.0:
                            commission_amount = (amount_total * commission_rule.commission_per) / 100
                            commission_amount = commission_amount if record.move_type == 'out_invoice' else -commission_amount
                            sale_commission_line_pool.create({
                                'invoice_id': record.id,
                                'user_id': record.invoice_user_id.id,
                                'date': fields.Date.today(),
                                'commission_id': commission.id,
                                'commission_rule_id': commission_rule.id,
                                'company_id': record.company_id.id,
                                'commission_type': commission_rule.commission_type,
                                'amount': commission_amount,
                                'sub_total': amount_total if record.move_type == 'out_invoice' else -amount_total,
                                'sale_commission_id': sale_commission and sale_commission.id or False,
                            })
                    elif commission_rule.commission_type == 'adjusted_sale_value_discount' and not record.is_new_customer and commission_rule.adjusted_amount_rate_per > 0.0:
                        amount_total = sum(record.invoice_line_ids.filtered(lambda x: not x.is_new_product 
                            and x.product_id 
                            and x.product_id.categ_id.id in commission_rule.product_category_ids.ids
                            and x.discount >= commission_rule.min_discount
                            and x.discount <= commission_rule.max_discount).mapped('price_total'))
                        if amount_total > 0.0:
                            adjusted_amount = (amount_total * commission_rule.adjusted_amount_rate_per) / 100
                            adjusted_amount = adjusted_amount if record.move_type == 'out_invoice' else -adjusted_amount
                            sale_commission_line_pool.create({
                                'invoice_id': record.id,
                                'user_id': record.invoice_user_id.id,
                                'date': fields.Date.today(),
                                'commission_id': commission.id,
                                'commission_rule_id': commission_rule.id,
                                'company_id': record.company_id.id,
                                'commission_type': commission_rule.commission_type,
                                'adjusted_amount': adjusted_amount,
                                'sub_total': amount_total if record.move_type == 'out_invoice' else -amount_total,
                                'sale_commission_id': sale_commission and sale_commission.id or False,
                            })

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_new_product = fields.Boolean(string='New Product', copy=True)
    is_new_customer = fields.Boolean(string='New Customer', related='move_id.is_new_customer', store=True)
    commission_code = fields.Char(string='Commission code', compute='_compute_commission_code', store=True)

    @api.depends('move_id.commission_lines', 'move_id.is_new_customer', 'is_new_product')
    def _compute_commission_code(self):
        for record in self:
            record.commission_code = ''
            if record.move_id.is_new_customer:
                commission_line = record.move_id.commission_lines.filtered(lambda x: x.commission_type == 'new_customer')
                if commission_line:
                    record.commission_code = commission_line[0].commission_rule_id.name
            elif not record.move_id.is_new_customer and record.is_new_product:
                commission_line = record.move_id.commission_lines.filtered(lambda x: x.commission_type == 'new_product')
                if commission_line:
                    record.commission_code = commission_line[0].commission_rule_id.name
            elif not record.move_id.is_new_customer and not record.is_new_product:
                commission_line = record.move_id.commission_lines.filtered(lambda x: x.commission_type in ['adjusted_sale_value_discount', 'adjusted_sale_value_fixed'])
                if commission_line:
                    record.commission_code = commission_line[0].commission_rule_id.name
