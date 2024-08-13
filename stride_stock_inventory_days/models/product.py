from odoo import models, fields, api,_
from dateutil.relativedelta import relativedelta
from odoo.tools import float_round

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    average_sold = fields.Float(string='Average Sold per day', compute='_compute_quantities')
    days_of_inventory = fields.Float(string='Days of Inventory', compute='_compute_quantities')

    @api.depends(
        'product_variant_ids.qty_available',
        'product_variant_ids.virtual_available',
        'product_variant_ids.incoming_qty',
        'product_variant_ids.outgoing_qty',
        'product_variant_ids.average_sold',
        'product_variant_ids.days_of_inventory',
    )
    def _compute_quantities(self):
        super()._compute_quantities()
        res = self._compute_quantities_dict()
        for template in self:
            template.average_sold = res[template.id]['average_sold']
            template.days_of_inventory = res[template.id]['days_of_inventory']

    def _compute_quantities_dict(self):
        variants_available = {
            p['id']: p for p in self.product_variant_ids._origin.read(
                ['qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty',
                 'average_sold', 'days_of_inventory'])
        }
        prod_available = {}
        for template in self:
            qty_available = 0
            average_sold = 0
            virtual_available = 0
            incoming_qty = 0
            outgoing_qty = 0
            days_of_inventory = 0
            for p in template.product_variant_ids._origin:
                qty_available += variants_available[p.id]["qty_available"]
                virtual_available += variants_available[p.id]["virtual_available"]
                incoming_qty += variants_available[p.id]["incoming_qty"]
                outgoing_qty += variants_available[p.id]["outgoing_qty"]
                average_sold += variants_available[p.id]["average_sold"]
                days_of_inventory += variants_available[p.id]["days_of_inventory"]
            prod_available[template.id] = {
                "qty_available": qty_available,
                "virtual_available": virtual_available,
                "incoming_qty": incoming_qty,
                "outgoing_qty": outgoing_qty,
                "average_sold": average_sold,
                "days_of_inventory": days_of_inventory,
            }
        return prod_available


class ProductProduct(models.Model):
    _inherit = 'product.product'

    average_sold = fields.Float(string='Average Sold Per Day', compute='_compute_quantities')
    days_of_inventory = fields.Float(string='Days of Inventory', compute='_compute_quantities')

    def _compute_quantities(self):
        super()._compute_quantities()
        products = self.with_context(prefetch_fields=False).filtered(lambda p: p.type != 'service').with_context(
            prefetch_fields=True)
        res = products._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'),
                                                self._context.get('package_id'), self._context.get('from_date'),
                                                self._context.get('to_date'))
        for product in products:
            product.update(res[product.id])
        services = self - products
        services.average_sold = 0.0
        services.days_of_inventory = 0.0

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        res = super()._compute_quantities_dict(lot_id, owner_id, package_id, from_date, to_date)
        for product in self.with_context(prefetch_fields=False):
            rounding = product.uom_id.rounding
            to_date = fields.Date.today()
            from_date = to_date - relativedelta(days=30)
            domain = [('product_id', '=', product.id), ('date', '>=', from_date), ('date', '>=', to_date), ('state','not in', ['draft', 'cancel', 'sent'])]
            sale_report = self.env['sale.report'].search(domain)
            total_sold_qty = sum(sale_report.mapped('product_uom_qty'))
            no_of_days = self.company_id.average_no_of_days or 30
            if product.categ_id.average_no_of_days:
                no_of_days = product.categ_id.average_no_of_days
            average_sold = total_sold_qty / no_of_days
            days_of_inventory = 0
            if average_sold:
                days_of_inventory = res[product.id]['free_qty'] / average_sold
            res[product.id]['average_sold'] = float_round(average_sold, precision_rounding=rounding)
            res[product.id]['days_of_inventory'] = float_round(days_of_inventory, precision_rounding=rounding)
        return res
