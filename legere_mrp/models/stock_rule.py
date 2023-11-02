from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.tools import float_compare, OrderedSet

from odoo.addons.stock.models.stock_rule import StockRule

@api.model
def _run_pull(self, procurements):
    moves_values_by_company = defaultdict(list)
    mtso_products_by_locations = defaultdict(list)

    # To handle the `mts_else_mto` procure method, we do a preliminary loop to
    # isolate the products we would need to read the forecasted quantity,
    # in order to to batch the read. We also make a sanitary check on the
    # `location_src_id` field.
    for procurement, rule in procurements:
        if not rule.location_src_id:
            msg = _('No source location defined on stock rule: %s!') % (rule.name, )
            raise ProcurementException([(procurement, msg)])

        if rule.procure_method == 'mts_else_mto':
            mtso_products_by_locations[rule.location_src_id].append(procurement.product_id.id)

    # Get the forecasted quantity for the `mts_else_mto` procurement.
    forecasted_qties_by_loc = {}
    for location, product_ids in mtso_products_by_locations.items():
        products = self.env['product.product'].browse(product_ids).with_context(location=location.id)
        forecasted_qties_by_loc[location] = {product.id: product.free_qty for product in products}

    # Prepare the move values, adapt the `procure_method` if needed.
    procurements = sorted(procurements, key=lambda proc: float_compare(proc[0].product_qty, 0.0, precision_rounding=proc[0].product_uom.rounding) > 0)
    for procurement, rule in procurements:
        procure_method = rule.procure_method
        if rule.procure_method == 'mts_else_mto':
            qty_needed = procurement.product_uom._compute_quantity(procurement.product_qty, procurement.product_id.uom_id)
            if float_compare(qty_needed, 0, precision_rounding=procurement.product_id.uom_id.rounding) <= 0:
                procure_method = 'make_to_order'
                for move in procurement.values.get('group_id', self.env['procurement.group']).stock_move_ids:
                    if move.rule_id == rule and float_compare(move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding) > 0:
                        procure_method = move.procure_method
                        break
                forecasted_qties_by_loc[rule.location_src_id][procurement.product_id.id] -= qty_needed
            elif float_compare(qty_needed, forecasted_qties_by_loc[rule.location_src_id][procurement.product_id.id],
                               precision_rounding=procurement.product_id.uom_id.rounding) > 0:
                procure_method = 'make_to_order'
            else:
                forecasted_qties_by_loc[rule.location_src_id][procurement.product_id.id] -= qty_needed
                procure_method = 'make_to_stock'

        move_values = rule._get_stock_move_values(*procurement)
        move_values['procure_method'] = procure_method
        moves_values_by_company[procurement.company_id.id].append(move_values)

    for company_id, moves_values in moves_values_by_company.items():
        new_move_values = []
        product_list = []
        origin_list = []
        for moves_value in sorted(moves_values, key=lambda x: x.get('product_id'), reverse=False):
            if moves_value.get('product_id') in product_list and moves_value.get('origin') in origin_list:
                for new_move_value in new_move_values:
                    if new_move_value.get('product_id') == moves_value.get('product_id') and new_move_value.get('origin') == moves_value.get('origin'):
                        new_move_value['product_uom_qty'] = new_move_value['product_uom_qty'] + moves_value['product_uom_qty']
            else:
                product_list.append(moves_value.get('product_id'))
                origin_list.append(moves_value.get('origin'))
                new_move_values.append(moves_value)
        # create the move as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
        moves = self.env['stock.move'].with_user(SUPERUSER_ID).sudo().with_company(company_id).create(new_move_values)
        # Since action_confirm launch following procurement_group we should activate it.
        moves._action_confirm()
    return True

StockRule._run_pull = _run_pull