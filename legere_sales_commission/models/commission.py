import calendar
from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta

class Commission(models.Model):
    _name = "commission.commission"
    _description = "Commission"

    name = fields.Char(string='Name', required=True)
    user_ids = fields.Many2many('res.users', string='Salesperson', required=True, domain="[('share', '=', False)]")
    commission_rule_ids = fields.One2many('commission.rule', 'commission_id', string='Commission Rule')
    commission_allocation_ids = fields.One2many('commission.allocation', 'commission_id', string='Commission Allocation')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

class CommissionRule(models.Model):
    _name = "commission.rule"
    _description = "Commission Rule"

    commission_id = fields.Many2one('commission.commission', string='Commission', ondelete='cascade')
    commission_type = fields.Selection([('new_customer', 'New Customer'),
        ('new_product', 'New Product'),
        ('adjusted_sale_value_discount', 'Adjusted Sale Value (Based On Sales Discounts)'),
        ('adjusted_sale_value_fixed', 'Adjusted Sale Value (Fixed %)')], string='Commission Type', default='new_customer', required=True)
    commission_per = fields.Float(string='Commission (%)')
    product_category_ids = fields.Many2many('product.category', string='Product Category')
    adjusted_amount_rate_per = fields.Float(string='Adjusted Amount Rate (%)')
    min_discount = fields.Float(string='Min Discount (%)')
    max_discount = fields.Float(string='Max Discount (%)')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')

class CommissionAllocation(models.Model):
    _name = "commission.allocation"
    _description = "Commission Allocation"

    commission_id = fields.Many2one('commission.commission', string='Commission', ondelete='cascade')
    min_amount = fields.Monetary(string='Min Amount', required=True)
    max_amount = fields.Monetary(string='Max Amount', required=True)
    commission_per = fields.Float(string='Commission (%)', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')

class SaleCommission(models.Model):
    _name = "sale.commission"
    _description = "Sale Commission"
    _rec_name = 'user_id'

    #Commissions should be computed when they are created
    # @api.depends('lines', 'lines.amount')
    # def _compute_commission_amount(self):
    #     for record in self:
    #         record.commission_amount = sum(record.lines.mapped('amount'))

    user_id = fields.Many2one('res.users', string='Salesperson', required=True)
    from_date = fields.Date(string='From Date', required=True)
    to_date = fields.Date(string='To Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')
    commission_amount = fields.Monetary(string='Commission Amount')
    lines = fields.One2many('sale.commission.line', 'sale_commission_id', string='Sale Commission Lines', readonly=True)

class SaleCommissionLine(models.Model):
    _name = "sale.commission.line"
    _description = "Sale Commission Line"

    invoice_id = fields.Many2one('account.move', string='Invoice', required=True, ondelete='cascade')
    commission_id = fields.Many2one('commission.commission', string='Commission')
    commission_rule_id = fields.Many2one('commission.rule', string='Commission Rule')
    user_id = fields.Many2one('res.users', string='Salesperson', required=True)
    commission_type = fields.Selection([('new_customer', 'New Customer'),
        ('new_product', 'New Product'),
        ('adjusted_sale_value_discount', 'Adjusted Sale Value (Based On Sales Discounts)'),
        ('adjusted_sale_value_fixed', 'Adjusted Sale Value (Fixed %)')], string='Commission Type', default='new_customer', required=True)
    date = fields.Date(string='Date', required=True)
    sale_commission_id = fields.Many2one('sale.commission', string='Sale Commission', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')
    amount = fields.Monetary(string='Amount')
    adjusted_amount = fields.Monetary(string='Adjusted Amount')

    def generate_monthly_sales_commission(self):
        sale_commission_pool = self.env['sale.commission']
        current_date = datetime.today().date() - relativedelta(months=1)
        start_date = current_date.replace(day=1)
        end_date = current_date.replace(day=calendar.monthrange(current_date.year, current_date.month)[1])
        lines = self.env['sale.commission.line'].search([('date', '>=', start_date),
            ('date', '<=', end_date), 
            ('sale_commission_id', '=', False)])
        user_ids = lines.mapped('user_id')
        for user in user_ids:
            commission_amount = sum(lines.filtered(lambda x: x.user_id.id == user.id and x.commission_type != 'adjusted_sale_value_fixed').mapped('amount'))
            adjusted_amount = sum(lines.filtered(lambda x: x.user_id.id == user.id and x.commission_type == 'adjusted_sale_value_fixed').mapped('adjusted_amount'))
            
            if adjusted_amount > 0.0:
                commission_allocations = self.env['commission.allocation'].search([('commission_id', '=', lines.filtered(lambda x: x.commission_type == 'adjusted_sale_value_discount')[0].commission_id.id)], order='commission_per asc')
                for commission_allocation in commission_allocations:
                    if adjusted_amount > 0.0:
                        allocation_range_amount = (commission_allocation.max_amount - commission_allocation.min_amount)
                        if commission_allocation.commission_per > 0.0:
                            if adjusted_amount > allocation_range_amount:
                                commission_amount += ((allocation_range_amount * commission_allocation.commission_per) / 100)
                            else:
                                commission_amount += ((adjusted_amount * commission_allocation.commission_per) / 100)
                        adjusted_amount = adjusted_amount - allocation_range_amount
            sale_commission = sale_commission_pool.search([('from_date', '=', start_date),
                ('to_date', '=', end_date), ('user_id', '=', user.id)], limit=1)
            if not sale_commission:
                sale_commission = sale_commission_pool.create({
                    'user_id': user.id,
                    'from_date': start_date,
                    'to_date': end_date,
                    'company_id': lines[0].company_id.id,
                    'commission_amount': commission_amount
                })
            lines.filtered(lambda x: x.user_id.id == user.id).write({'sale_commission_id': sale_commission.id})