from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.tools import float_compare, OrderedSet

class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _run_manufacture(self, procurements):
        productions_values_by_company = defaultdict(list)
        for procurement, rule in procurements:
            if float_compare(procurement.product_qty, 0, precision_rounding=procurement.product_uom.rounding) <= 0:
                # If procurement contains negative quantity, don't create a MO that would be for a negative value.
                continue
            bom = rule._get_matching_bom(procurement.product_id, procurement.company_id, procurement.values)
            productions_values_by_company[procurement.company_id.id].append(rule._prepare_mo_vals(*procurement, bom))

        for company_id, productions_values in productions_values_by_company.items():
            for productions_value in productions_values:
                production_order = self.env['mrp.production'].sudo().search([('product_id', '=', productions_value.get('product_id')),
                    ('company_id', '=', company_id),
                    ('origin', '=', productions_value.get('origin')),
                    ('state', '=', 'draft')], limit=1)
                if production_order:
                    production_order.write({'product_qty': production_order.product_qty + productions_value.get('product_qty')})
                else:
                    # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
                    productions = self.env['mrp.production'].with_user(SUPERUSER_ID).sudo().with_company(company_id).create(productions_value)
                    #productions.filtered(self._should_auto_confirm_procurement_mo).action_confirm()
                    for production in productions:
                        origin_production = production.move_dest_ids and production.move_dest_ids[0].raw_material_production_id or False
                        orderpoint = production.orderpoint_id
                        if orderpoint and orderpoint.create_uid.id == SUPERUSER_ID and orderpoint.trigger == 'manual':
                            production.message_post(
                                body=_('This production order has been created from Replenishment Report.'),
                                message_type='comment',
                                subtype_xmlid='mail.mt_note')
                        elif orderpoint:
                            production.message_post_with_view(
                                'mail.message_origin_link',
                                values={'self': production, 'origin': orderpoint},
                                subtype_id=self.env.ref('mail.mt_note').id)
                        elif origin_production:
                            production.message_post_with_view(
                                'mail.message_origin_link',
                                values={'self': production, 'origin': origin_production},
                                subtype_id=self.env.ref('mail.mt_note').id)
        return True