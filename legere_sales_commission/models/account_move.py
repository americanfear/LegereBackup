from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = "account.move"

    is_new_customer = fields.Boolean(string='New Customer', copy=False)
    commission_lines = fields.One2many('sale.commission.line', 'invoice_id', string='Sale Commission Lines', readonly=True)

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for record in self.filtered(lambda x: x.move_type == 'out_invoice' and x.invoice_user_id):
            record.create_commission_lines()
        return res

    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        for record in self.filtered(lambda x: x.commission_lines):
            record.commission_lines.unlink()
        return res

    def unlink(self):
        for record in self:
            record.commission_lines.unlink()
        return super(AccountMove, self).unlink()

    def create_commission_lines(self):
        sale_commission_line_pool = self.env['sale.commission.line']
        for record in self:
            commission_ids = self.env['commission.commission'].search([('active', '=', True)]).filtered(lambda x: record.invoice_user_id.id in x.user_ids.ids)
            for commission in commission_ids:
                for commission_rule in commission.commission_rule_ids:
                    if commission_rule.commission_type == 'new_customer' and commission_rule.commission_per > 0.0 and record.is_new_customer:
                        sale_commission_line_pool.create({
                            'invoice_id': record.id,
                            'user_id': record.invoice_user_id.id,
                            'date': fields.Date.today(),
                            'company_id': record.company_id.id,
                            'commission_id': commission.id,
                            'commission_rule_id': commission_rule.id,
                            'commission_type': commission_rule.commission_type,
                            'amount': (record.amount_total * commission_rule.commission_per) / 100
                        })
                    elif commission_rule.commission_type == 'new_product' and commission_rule.commission_per > 0.0 and record.invoice_line_ids.filtered(lambda x: x.is_new_product) and not record.is_new_customer:
                        amount_total = sum(record.invoice_line_ids.filtered(lambda x: x.is_new_product).mapped('price_total'))
                        sale_commission_line_pool.create({
                            'invoice_id': record.id,
                            'user_id': record.invoice_user_id.id,
                            'date': fields.Date.today(),
                            'commission_id': commission.id,
                            'commission_rule_id': commission_rule.id,
                            'company_id': record.company_id.id,
                            'commission_type': commission_rule.commission_type,
                            'amount': (amount_total * commission_rule.commission_per) / 100
                        })
                    elif commission_rule.commission_type == 'adjusted_sale_value_fixed' and not record.is_new_customer and commission_rule.commission_per > 0.0:
                        amount_total = sum(record.invoice_line_ids.filtered(lambda x: not x.is_new_product 
                            and x.product_id 
                            and x.product_id.categ_id.id in commission_rule.product_category_ids.ids
                            and x.discount >= commission_rule.min_discount
                            and x.discount <= commission_rule.max_discount).mapped('price_total'))
                        if amount_total > 0.0:
                            sale_commission_line_pool.create({
                                'invoice_id': record.id,
                                'user_id': record.invoice_user_id.id,
                                'date': fields.Date.today(),
                                'commission_id': commission.id,
                                'commission_rule_id': commission_rule.id,
                                'company_id': record.company_id.id,
                                'commission_type': commission_rule.commission_type,
                                'amount': (amount_total * commission_rule.commission_per) / 100
                            })
                    elif commission_rule.commission_type == 'adjusted_sale_value_discount' and not record.is_new_customer and commission_rule.adjusted_amount_rate_per > 0.0:
                        amount_total = sum(record.invoice_line_ids.filtered(lambda x: not x.is_new_product 
                            and x.product_id 
                            and x.product_id.categ_id.id in commission_rule.product_category_ids.ids
                            and x.discount >= commission_rule.min_discount
                            and x.discount <= commission_rule.max_discount).mapped('price_total'))
                        if amount_total > 0.0:
                            sale_commission_line_pool.create({
                                'invoice_id': record.id,
                                'user_id': record.invoice_user_id.id,
                                'date': fields.Date.today(),
                                'commission_id': commission.id,
                                'commission_rule_id': commission_rule.id,
                                'company_id': record.company_id.id,
                                'commission_type': commission_rule.commission_type,
                                'adjusted_amount': (amount_total * commission_rule.adjusted_amount_rate_per) / 100
                            })

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_new_product = fields.Boolean(string='New Product', copy=False)
