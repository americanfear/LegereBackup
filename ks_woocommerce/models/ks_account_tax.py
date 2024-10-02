import logging

from odoo import api, fields, models, _, Command
from odoo.tools.float_utils import float_round as round

_logger = logging.getLogger(__name__)


class KsAccountTax(models.Model):
    _inherit = "account.tax"

    def ks_woo_get_all_account_tax(self, instance, include=False):
        """
        Use: This function will get all the tax from WooCommerce
           :woo_instance: woo instance
           :include : parameter to filter out records
           :return: Dictionary of Created Woo tax
           :rtype: dict
                       """
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = []
        try:
            if include:
                include = include.split(",")
                for rec in include:
                    wc_api = instance.ks_woo_api_authentication()
                    taxes_data_response = wc_api.get("taxes/%s" % rec)
                    if taxes_data_response.status_code in [200, 201]:
                        all_retrieved_data.append(taxes_data_response.json())
                    else:
                        self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                           status="failed",
                                                                           type="tax",
                                                                           operation_flow="woo_to_odoo",
                                                                           instance=instance,
                                                                           woo_id=0,
                                                                           message=str(taxes_data_response.text))
            else:
                params = {'per_page': per_page,
                          'page': page}
                while multi_api_call:
                    wc_api = instance.ks_woo_api_authentication()
                    taxes_data_response = wc_api.get("taxes", params=params)
                    if taxes_data_response.status_code in [200, 201]:
                        all_retrieved_data.extend(taxes_data_response.json())
                    else:
                        self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                           status="failed",
                                                                           type="tax",
                                                                           operation_flow="woo_to_odoo",
                                                                           instance=instance,
                                                                           woo_id=0,
                                                                           message=str(taxes_data_response.text))
                    total_api_calls = taxes_data_response.headers._store.get('x-wp-totalpages')[1]
                    remaining_api_calls = int(total_api_calls) - page
                    if remaining_api_calls > 0:
                        page += 1
                    else:
                        multi_api_call = False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="tax",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="tax",
                                                               operation_flow="woo_to_odoo",
                                                               instance=instance,
                                                               woo_id=0,
                                                               message="Fetch of Category successful")
        return all_retrieved_data

    def ks_get_tax_ids(self, instance, data):
        """
        Creates and Updates the tax in the odoo side
        :param instance: woo instance
        :param data: the tax data from woocommerce
        :return: tax
        """
        tax_exist = self.env['account.tax']
        if data:
            tax_exist = tax_exist.search([('ks_woo_id', '=', data.get('id')),
                                                        ('ks_wc_instance', '=', instance.id)], limit=1)
            try:
                tax_value = self.env['ir.config_parameter'].sudo().get_param(
                    'account.show_line_subtotals_tax_selection')
                if tax_value == 'tax_excluded':
                    price_include = False
                elif tax_value == 'tax_included':
                    price_include = True
                else:
                    price_include = False
                ks_name = (str(data.get('country')) + '-' + str(data.get('name') + '-' + str(data.get('priority'))))
                woo_tax_data = {
                    'name': ks_name.upper(),
                    'ks_woo_id': data.get('id'),
                    'ks_wc_instance': instance.id,
                    'amount': float(data.get('rate') or 0),
                    'amount_type': 'percent',
                    'company_id': instance.ks_company_id.id,
                    'type_tax_use': 'sale',
                    'active': True,
                    'price_include': price_include,
                }
                if tax_exist:
                    tax_exist.write(woo_tax_data)
                else:
                    tax_exist = self.env['account.tax'].create(woo_tax_data)
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                              ks_woo_instance=instance,
                                                              ks_record_id=0,
                                                              ks_message='Create/Fetch of Taxes Failed',
                                                              ks_woo_id=0,
                                                              ks_operation_flow='woo_to_odoo',
                                                              ks_status="failed",
                                                              ks_type="system_status",
                                                              ks_error=e)
        return tax_exist


    @api.model
    def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False,
                                       early_pay_discount_computation=None, early_pay_discount_percentage=None):
        ks_discount_amount = 0
        if base_line.get('ks_discount_amount', False):
            ks_discount_amount = base_line['ks_discount_amount']
        orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        orig_price_unit_after_discount = orig_price_unit_after_discount
        price_unit_after_discount = orig_price_unit_after_discount
        taxes = base_line['taxes']._origin
        taxes = taxes.with_context(ks_discount_amount=ks_discount_amount)
        currency = base_line['currency'] or self.env.company.currency_id
        rate = base_line['rate']

        if early_pay_discount_computation in ('included', 'excluded'):
            remaining_part_to_consider = (100 - early_pay_discount_percentage) / 100.0
            price_unit_after_discount = remaining_part_to_consider * price_unit_after_discount

        if taxes:

            if handle_price_include is None:
                manage_price_include = bool(base_line['handle_price_include'])
            else:
                manage_price_include = handle_price_include

            taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                price_unit_after_discount,
                currency=currency,
                quantity=base_line['quantity'],
                product=base_line['product'],
                partner=base_line['partner'],
                is_refund=base_line['is_refund'],
                handle_price_include=manage_price_include,
                include_caba_tags=include_caba_tags,
            )

            to_update_vals = {
                'tax_tag_ids': [Command.set(taxes_res['base_tags'])],
                'price_subtotal': taxes_res['total_excluded'],
                'price_total': taxes_res['total_included'],
            }

            if early_pay_discount_computation == 'excluded':
                new_taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                    orig_price_unit_after_discount,
                    currency=currency,
                    quantity=base_line['quantity'],
                    product=base_line['product'],
                    partner=base_line['partner'],
                    is_refund=base_line['is_refund'],
                    handle_price_include=manage_price_include,
                    include_caba_tags=include_caba_tags,
                )
                for tax_res, new_taxes_res in zip(taxes_res['taxes'], new_taxes_res['taxes']):
                    delta_tax = new_taxes_res['amount'] - tax_res['amount']
                    tax_res['amount'] += delta_tax
                    to_update_vals['price_total'] += delta_tax

            tax_values_list = []
            for tax_res in taxes_res['taxes']:
                tax_amount = tax_res['amount'] / rate
                if self.company_id.tax_calculation_rounding_method == 'round_per_line':
                    tax_amount = currency.round(tax_amount)
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_res['tax_repartition_line_id'])
                tax_values_list.append({
                    **tax_res,
                    'tax_repartition_line': tax_rep,
                    'base_amount_currency': tax_res['base'],
                    'base_amount': currency.round(tax_res['base'] / rate),
                    'tax_amount_currency': tax_res['amount'],
                    'tax_amount': tax_amount,
                })


        else:
            if ks_discount_amount:
                price_subtotal = currency.round((price_unit_after_discount *base_line['quantity']) - ks_discount_amount)
            else:
                price_subtotal = currency.round(price_unit_after_discount * base_line['quantity'])
            to_update_vals = {
                'tax_tag_ids': [Command.clear()],
                'price_subtotal': price_subtotal,
                'price_total': price_subtotal,
            }
            tax_values_list = []

        return to_update_vals, tax_values_list

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False,
                    handle_price_include=True, include_caba_tags=False, fixed_multiplicator=1):

        if not self:
            company = self.env.company
        else:
            company = self[0].company_id

        taxes, groups_map = self.flatten_taxes_hierarchy(create_map=True)
        if not currency:
            currency = company.currency_id

        prec = currency.rounding
        round_tax = False if company.tax_calculation_rounding_method == 'round_globally' else True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])

        if not round_tax:
            prec *= 1e-5

        def recompute_base(base_amount, fixed_amount, percent_amount, division_amount):
            return (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) * (100 - division_amount) / 100

        ks_amount = (price_unit * quantity)
        if self._context.get('ks_discount_amount', False):
            ks_amount = ks_amount - self._context.get('ks_discount_amount')
        base = currency.round(ks_amount)
        sign = 1
        if currency.is_zero(base):
            sign = -1 if fixed_multiplicator < 0 else 1
        elif base < 0:
            sign = -1
            base = -base
        total_included_checkpoints = {}
        i = len(taxes) - 1
        store_included_tax_total = True
        incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
        cached_tax_amounts = {}
        if handle_price_include:
            for tax in reversed(taxes):
                tax_repartition_lines = (
                        is_refund
                        and tax.refund_repartition_line_ids
                        or tax.invoice_repartition_line_ids
                ).filtered(lambda x: x.repartition_type == "tax")
                sum_repartition_factor = sum(tax_repartition_lines.mapped("factor"))

                if tax.include_base_amount:
                    base = recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount)
                    incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
                    store_included_tax_total = True
                if tax.price_include or self._context.get('force_price_include'):
                    if tax.amount_type == 'percent':
                        incl_percent_amount += tax.amount * sum_repartition_factor
                    elif tax.amount_type == 'division':
                        incl_division_amount += tax.amount * sum_repartition_factor
                    elif tax.amount_type == 'fixed':
                        incl_fixed_amount += abs(quantity) * tax.amount * sum_repartition_factor * abs(
                            fixed_multiplicator)
                    else:

                        tax_amount = tax._compute_amount(base, sign * price_unit, quantity, product, partner,
                                                         fixed_multiplicator) * sum_repartition_factor
                        incl_fixed_amount += tax_amount
                        cached_tax_amounts[i] = tax_amount
                    if store_included_tax_total and (
                            tax.amount or tax.amount_type not in ("percent", "division", "fixed")
                    ):
                        total_included_checkpoints[i] = base
                        store_included_tax_total = False
                i -= 1

        total_excluded = currency.round(
            recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount))
        base = total_included = total_void = total_excluded
        skip_checkpoint = False
        product_tag_ids = product.account_tag_ids.ids if product else []
        taxes_vals = []
        i = 0
        cumulated_tax_included_amount = 0
        for tax in taxes:
            price_include = self._context.get('force_price_include', tax.price_include)

            if price_include or tax.is_base_affected:
                tax_base_amount = base
            else:
                tax_base_amount = total_excluded
            tax_repartition_lines = (
                    is_refund and tax.refund_repartition_line_ids or tax.invoice_repartition_line_ids).filtered(
                lambda x: x.repartition_type == 'tax')
            sum_repartition_factor = sum(tax_repartition_lines.mapped('factor'))
            if not skip_checkpoint and price_include and total_included_checkpoints.get(
                    i) is not None and sum_repartition_factor != 0:
                tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount)
                cumulated_tax_included_amount = 0
            else:
                tax_amount = tax.with_context(force_price_include=False)._compute_amount(
                    tax_base_amount, sign * price_unit, quantity, product, partner, fixed_multiplicator)
            tax_amount = round(tax_amount, precision_rounding=prec)
            factorized_tax_amount = round(tax_amount * sum_repartition_factor, precision_rounding=prec)

            if price_include and total_included_checkpoints.get(i) is None:
                cumulated_tax_included_amount += factorized_tax_amount

            subsequent_taxes = self.env['account.tax']
            subsequent_tags = self.env['account.account.tag']
            if tax.include_base_amount:
                subsequent_taxes = taxes[i + 1:].filtered('is_base_affected')

                taxes_for_subsequent_tags = subsequent_taxes

                if not include_caba_tags:
                    taxes_for_subsequent_tags = subsequent_taxes.filtered(lambda x: x.tax_exigibility != 'on_payment')

                subsequent_tags = taxes_for_subsequent_tags.get_tax_tags(is_refund, 'base')

            repartition_line_amounts = [round(tax_amount * line.factor, precision_rounding=prec) for line in
                                        tax_repartition_lines]
            total_rounding_error = round(factorized_tax_amount - sum(repartition_line_amounts), precision_rounding=prec)
            nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
            rounding_error = round(nber_rounding_steps and total_rounding_error / nber_rounding_steps or 0.0,
                                   precision_rounding=prec)

            for repartition_line, line_amount in zip(tax_repartition_lines, repartition_line_amounts):

                if nber_rounding_steps:
                    line_amount += rounding_error
                    nber_rounding_steps -= 1

                if not include_caba_tags and tax.tax_exigibility == 'on_payment':
                    repartition_line_tags = self.env['account.account.tag']
                else:
                    repartition_line_tags = repartition_line.tag_ids

                taxes_vals.append({
                    'id': tax.id,
                    'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                    'amount': sign * line_amount,
                    'base': round(sign * tax_base_amount, precision_rounding=prec),
                    'sequence': tax.sequence,
                    'account_id': repartition_line._get_aml_target_tax_account().id,
                    'analytic': tax.analytic,
                    'use_in_tax_closing': repartition_line.use_in_tax_closing,
                    'price_include': price_include,
                    'tax_exigibility': tax.tax_exigibility,
                    'tax_repartition_line_id': repartition_line.id,
                    'group': groups_map.get(tax),
                    'tag_ids': (repartition_line_tags + subsequent_tags).ids + product_tag_ids,
                    'tax_ids': subsequent_taxes.ids,
                })

                if not repartition_line.account_id:
                    total_void += line_amount

            if tax.include_base_amount:
                base += factorized_tax_amount
                if not price_include:
                    skip_checkpoint = True

            total_included += factorized_tax_amount
            i += 1

        base_taxes_for_tags = taxes
        if not include_caba_tags:
            base_taxes_for_tags = base_taxes_for_tags.filtered(lambda x: x.tax_exigibility != 'on_payment')

        base_rep_lines = base_taxes_for_tags.mapped(
            is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids').filtered(
            lambda x: x.repartition_type == 'base')

        return {
            'base_tags': base_rep_lines.tag_ids.ids + product_tag_ids,
            'taxes': taxes_vals,
            'total_excluded': sign * total_excluded,
            'total_included': sign * currency.round(total_included),
            'total_void': sign * currency.round(total_void),
        }
