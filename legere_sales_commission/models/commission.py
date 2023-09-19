import calendar
from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta

class Commission(models.Model):
    _name = "commission.commission"
    _description = "Commission"

    name = fields.Char(string='Name', required=True)
    use_for_manager = fields.Boolean(string='Use for Manager')
    manager_id = fields.Many2one('res.users', string='Manager', domain="[('share', '=', False)]")
    new_sales_commission_per = fields.Float(string='New Sales Commission (%)', default=2.0)
    regular_sales_commission_per = fields.Float(string='Regular Sales Commission (%)', default=1.0)
    user_ids = fields.Many2many('res.users', string='Salespersons', required=True, domain="[('share', '=', False)]")
    commission_rule_ids = fields.One2many('commission.rule', 'commission_id', string='Commission Rule')
    commission_allocation_ids = fields.One2many('commission.allocation', 'commission_id', string='Commission Allocation')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

class CommissionRule(models.Model):
    _name = "commission.rule"
    _description = "Commission Rule"

    # def name_get(self):
    #     result = []
    #     for record in self:
    #         if record.commission_type == 'new_customer':
    #             name = 'New Customer'
    #         elif record.commission_type == 'new_product':
    #             name = 'New Customer'
    #         elif record.commission_type == 'adjusted_sale_value_discount':
    #             name = 'Adjusted Sale Value Based On Sales Discounts'
    #         elif record.commission_type == 'adjusted_sale_value_fixed':
    #             name = 'Adjusted Sale Value Fixed %'
    #         if record.product_category_ids:
    #             name += ' ('
    #             name += ', '.join([product_category.name for product_category in record.product_category_ids])
    #             name += ')'
    #         result.append((record.id, name))
    #     return result

    name = fields.Char('Code', required=True)
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
    commission_rule_ids = fields.Many2many('commission.rule', string='Commission Rules', domain="[('commission_id', '=', commission_id)]")

class SaleCommission(models.Model):
    _name = "sale.commission"
    _description = "Sale Commission"
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string='Salesperson', required=True)
    from_date = fields.Date(string='From Date', required=True)
    to_date = fields.Date(string='To Date', required=True)
    use_for_manager = fields.Boolean(string='Use for Manager')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')
    commission_amount = fields.Monetary(string='Commission Amount', compute=False)
    paid = fields.Boolean(string='Paid')
    lines = fields.One2many('sale.commission.line', 'sale_commission_id', string='Sale Commission Lines', readonly=True)
    user_lines = fields.One2many('sale.commission.user.line', 'sale_commission_id', string='Sale Commission User Lines', readonly=True)

    def recalculate_amount(self):
        commission_pool = self.env['commission.commission']
        sale_commission_pool = self.env['sale.commission']
        sale_commission_line_pool = self.env['sale.commission.line']
        sale_commission_user_line_pool = self.env['sale.commission.user.line']
        commission_allocation_pool = self.env['commission.allocation']
        for record in self:
            record.write({'commission_amount': 0.0})
            start_date = record.from_date
            end_date = record.to_date
            lines = record.lines
            commission_ids = lines.mapped('commission_id')
            for commission_id in commission_ids:
                user = record.user_id
                commission_amount = sum(lines.filtered(lambda x: x.commission_id.id == commission_id.id and x.user_id.id == user.id and x.commission_type != 'adjusted_sale_value_discount').mapped('amount'))
                adjusted_amount = sum(lines.filtered(lambda x: x.commission_id.id == commission_id.id and x.user_id.id == user.id and x.commission_type == 'adjusted_sale_value_discount').mapped('adjusted_amount'))
                other_amount = 0.0
                commission_allocations = commission_allocation_pool.search([('commission_id', '=', commission_id.id)], order='min_amount asc')
                for commission_allocation in commission_allocations:
                    previous_commission_allocations = commission_allocation_pool.search([('commission_id', '=', commission_id.id),
                        ('min_amount', '<', commission_allocation.min_amount)]).filtered(lambda x: x.commission_rule_ids.ids == commission_allocation.commission_rule_ids.ids)
                    for previous_commission_allocation in previous_commission_allocations:
                        if previous_commission_allocation.max_amount > 0.0:
                            allocation_range_amount = (previous_commission_allocation.max_amount - previous_commission_allocation.min_amount)
                        else:
                            allocation_range_amount = previous_commission_allocation.min_amount
                        adjusted_amount = adjusted_amount - allocation_range_amount
                    
                    if commission_allocation.commission_rule_ids:
                        other_amount = sum(lines.filtered(lambda x: x.commission_id.id == commission_id.id and x.commission_rule_id.id not in commission_allocation.commission_rule_ids.ids and x.user_id.id == user.id and x.commission_type == 'adjusted_sale_value_discount').mapped('adjusted_amount'))
                        adjusted_amount = adjusted_amount - other_amount
                    
                    if adjusted_amount > 0.0:
                        if commission_allocation.max_amount > 0.0:
                            allocation_range_amount = (commission_allocation.max_amount - commission_allocation.min_amount)
                        else:
                            allocation_range_amount = commission_allocation.min_amount

                        if commission_allocation.commission_per > 0.0:
                            if adjusted_amount > allocation_range_amount:
                                commission_amount += ((allocation_range_amount * commission_allocation.commission_per) / 100)
                            else:
                                commission_amount += ((adjusted_amount * commission_allocation.commission_per) / 100)
                        adjusted_amount = adjusted_amount + other_amount
                
                record.write({'commission_amount': (record.commission_amount + commission_amount)})

            if record.use_for_manager and record.user_lines:
                commission_amount = sum(record.user_lines.mapped('commission_amount'))
                record.write({'commission_amount': (record.commission_amount + commission_amount)})
            
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
    sale_commission_id = fields.Many2one('sale.commission', string='Sale Commission')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')
    sub_total = fields.Monetary(string='Sub Total')
    amount = fields.Monetary(string='Amount')
    adjusted_amount = fields.Monetary(string='Adjusted Amount')

    def generate_monthly_sales_commission(self):
        commission_pool = self.env['commission.commission']
        sale_commission_pool = self.env['sale.commission']
        sale_commission_line_pool = self.env['sale.commission.line']
        sale_commission_user_line_pool = self.env['sale.commission.user.line']
        commission_allocation_pool = self.env['commission.allocation']
        current_date = datetime.today().date() - relativedelta(months=1)
        start_date = current_date.replace(day=1)
        end_date = current_date.replace(day=calendar.monthrange(current_date.year, current_date.month)[1])
        lines = sale_commission_line_pool.search([('date', '>=', start_date),
            ('date', '<=', end_date), ('sale_commission_id', '=', False)])
        commission_ids = lines.mapped('commission_id')
        for commission_id in commission_ids:
            for user in commission_id.user_ids:
                commission_amount = sum(lines.filtered(lambda x: x.commission_id.id == commission_id.id and x.user_id.id == user.id and x.commission_type != 'adjusted_sale_value_discount').mapped('amount'))
                adjusted_amount = sum(lines.filtered(lambda x: x.commission_id.id == commission_id.id and x.user_id.id == user.id and x.commission_type == 'adjusted_sale_value_discount').mapped('adjusted_amount'))
                other_amount = 0.0
                commission_allocations = commission_allocation_pool.search([('commission_id', '=', commission_id.id)], order='commission_per asc')
                for commission_allocation in commission_allocations:
                    previous_commission_allocations = commission_allocation_pool.search([('commission_id', '=', commission_id.id),
                        ('min_amount', '<', commission_allocation.min_amount)]).filtered(lambda x: x.commission_rule_ids.ids == commission_allocation.commission_rule_ids.ids)
                    for previous_commission_allocation in previous_commission_allocations:
                        if previous_commission_allocation.max_amount > 0.0:
                            allocation_range_amount = (previous_commission_allocation.max_amount - previous_commission_allocation.min_amount)
                        else:
                            allocation_range_amount = previous_commission_allocation.min_amount
                        adjusted_amount = adjusted_amount - allocation_range_amount
                    
                    if commission_allocation.commission_rule_ids:
                        other_amount = sum(lines.filtered(lambda x: x.commission_id.id == commission_id.id and x.commission_rule_id.id not in commission_allocation.commission_rule_ids.ids and x.user_id.id == user.id and x.commission_type == 'adjusted_sale_value_discount').mapped('adjusted_amount'))
                        adjusted_amount = adjusted_amount - other_amount
                    
                    if adjusted_amount > 0.0:
                        if commission_allocation.max_amount > 0.0:
                            allocation_range_amount = (commission_allocation.max_amount - commission_allocation.min_amount)
                        else:
                            allocation_range_amount = commission_allocation.min_amount

                        if commission_allocation.commission_per > 0.0:
                            if adjusted_amount > allocation_range_amount:
                                commission_amount += ((allocation_range_amount * commission_allocation.commission_per) / 100)
                            else:
                                commission_amount += ((adjusted_amount * commission_allocation.commission_per) / 100)
                        adjusted_amount = adjusted_amount + other_amount
                
                sale_commission = sale_commission_pool.search([('from_date', '=', start_date),
                    ('to_date', '=', end_date), ('user_id', '=', user.id)], limit=1)
                if sale_commission:
                    sale_commission.write({'commission_amount': (sale_commission.commission_amount + commission_amount)})
                else:
                    sale_commission = sale_commission_pool.create({
                        'user_id': user.id,
                        'from_date': start_date,
                        'to_date': end_date,
                        'company_id': commission_id.company_id.id,
                        'commission_amount': commission_amount
                    })
                lines.filtered(lambda x: x.commission_id.id == commission_id.id and x.user_id.id == user.id).write({'sale_commission_id': sale_commission.id})

        
        commission_rules = commission_pool.search([('use_for_manager', '!=', False)])
        
        for commission_rule in commission_rules:
            commission_amount = 0.0
            lines = sale_commission_line_pool.search([('date', '>=', start_date),
                ('date', '<=', end_date), ('user_id', 'in', commission_rule.user_ids.ids)])
            if lines:
                new_sales_total = sum(lines.filtered(lambda x: x.commission_type in ['new_customer', 'new_product']).mapped('sub_total'))
                regular_sales_total = sum(lines.filtered(lambda x: x.commission_type in ['adjusted_sale_value_discount', 'adjusted_sale_value_fixed']).mapped('sub_total'))
                if new_sales_total > 0.0 and commission_rule.new_sales_commission_per > 0.0:
                    commission_amount += (new_sales_total * commission_rule.new_sales_commission_per) / 100
                if regular_sales_total > 0.0 and commission_rule.regular_sales_commission_per > 0.0:
                    commission_amount += (regular_sales_total * commission_rule.regular_sales_commission_per) / 100
                sale_commission = sale_commission_pool.search([('from_date', '=', start_date),
                        ('to_date', '=', end_date), ('user_id', '=', commission_rule.manager_id.id)], limit=1)
                if sale_commission:
                    sale_commission.write({'commission_amount': (sale_commission.commission_amount + commission_amount),
                        'use_for_manager': True})
                else:
                    sale_commission = sale_commission_pool.create({
                        'user_id': commission_rule.manager_id.id,
                        'use_for_manager': True,
                        'from_date': start_date,
                        'to_date': end_date,
                        'company_id': commission_rule.company_id.id,
                        'commission_amount': commission_amount
                    })
                
                users = lines.mapped('user_id')
                for user in users:
                    new_sales_total = sum(lines.filtered(lambda x: x.user_id.id == user.id and x.commission_type in ['new_customer', 'new_product']).mapped('sub_total'))
                    regular_sales_total = sum(lines.filtered(lambda x: x.user_id.id == user.id and x.commission_type in ['adjusted_sale_value_discount', 'adjusted_sale_value_fixed']).mapped('sub_total'))
                    if new_sales_total > 0.0 and commission_rule.new_sales_commission_per > 0.0:
                        commission_amount = (new_sales_total * commission_rule.new_sales_commission_per) / 100
                        
                        sale_commission_user_line_pool.create({
                            'name': 'New Sales',
                            'user_id': user.id,
                            'total_amount': new_sales_total,
                            'commission_amount': commission_amount,
                            'company_id': commission_rule.company_id.id,
                            'sale_commission_id': sale_commission.id
                        })

                    if regular_sales_total > 0.0 and commission_rule.regular_sales_commission_per > 0.0:
                        commission_amount = (regular_sales_total * commission_rule.regular_sales_commission_per) / 100

                        sale_commission_user_line_pool.create({
                            'name': 'Regular Sales',
                            'user_id': user.id,
                            'total_amount': regular_sales_total,
                            'commission_amount': commission_amount,
                            'company_id': commission_rule.company_id.id,
                            'sale_commission_id': sale_commission.id
                        })

class SaleCommissionUserLine(models.Model):
    _name = "sale.commission.user.line"
    _description = "Sale Commission User Line"

    name = fields.Char(string='Description', required=True)
    user_id = fields.Many2one('res.users', string='Salesperson', required=True)
    total_amount = fields.Monetary(string='Total')
    commission_amount = fields.Monetary(string='Commission')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')
    sale_commission_id = fields.Many2one('sale.commission', string='Sale Commission', ondelete='cascade')