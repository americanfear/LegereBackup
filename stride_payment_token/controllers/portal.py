import urllib.parse
import werkzeug

from odoo import _, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.portal import PaymentPortal

class CustomPaymentPortal(PaymentPortal):

    # Remove Me: This is added to fix issue of standard Odoo module and it can be removed once it will fixed by Odoo.
    def _get_custom_rendering_context_values(self, invoice_id=None, sale_order_id=None, **kwargs):
        if invoice_id:
            return super(CustomPaymentPortal, self)._get_custom_rendering_context_values(invoice_id=int(invoice_id), **kwargs)
        elif sale_order_id:
            return super(CustomPaymentPortal, self)._get_custom_rendering_context_values(sale_order_id=int(sale_order_id), **kwargs)
        else:
            return super(CustomPaymentPortal, self)._get_custom_rendering_context_values(**kwargs)

    @http.route(
        '/payment/pay', type='http', methods=['GET'], auth='public', website=True, sitemap=False,
    )
    def payment_pay(
        self, reference=None, amount=None, currency_id=None, partner_id=None, company_id=None,
        provider_id=None, access_token=None, **kwargs
    ):
        """ Display the payment form with optional filtering of payment options.

        The filtering takes place on the basis of provided parameters, if any. If a parameter is
        incorrect or malformed, it is skipped to avoid preventing the user from making the payment.

        In addition to the desired filtering, a second one ensures that none of the following
        rules is broken:
            - Public users are not allowed to save their payment method as a token.
            - Payments made by public users should either *not* be made on behalf of a specific
              partner or have an access token validating the partner, amount and currency.
        We let access rights and security rules do their job for logged in users.

        :param str reference: The custom prefix to compute the full reference
        :param str amount: The amount to pay
        :param str currency_id: The desired currency, as a `res.currency` id
        :param str partner_id: The partner making the payment, as a `res.partner` id
        :param str company_id: The related company, as a `res.company` id
        :param str provider_id: The desired provider, as a `payment.provider` id
        :param str access_token: The access token used to authenticate the partner
        :param dict kwargs: Optional data passed to helper methods.
        :return: The rendered checkout form
        :rtype: str
        :raise: werkzeug.exceptions.NotFound if the access token is invalid
        """
        # Cast numeric parameters as int or float and void them if their str value is malformed
        currency_id, provider_id, partner_id, company_id = tuple(map(
            self._cast_as_int, (currency_id, provider_id, partner_id, company_id)
        ))
        
        amount = self._cast_as_float(amount)
        # Raise an HTTP 404 if a partner is provided with an invalid access token
        if partner_id:
            if not payment_utils.check_access_token(access_token, partner_id, amount, currency_id):
                raise werkzeug.exceptions.NotFound()  # Don't leak information about ids.

        # Overwrite: Set partner from invoice or sale order
        if 'invoice_id' in kwargs:
            partner_id = request.env['account.move'].sudo().browse(int(kwargs.get('invoice_id'))).partner_id.id

        if 'sale_order_id' in kwargs:
            partner_id = request.env['sale.order'].sudo().browse(int(kwargs.get('sale_order_id'))).partner_id.id

        user_sudo = request.env.user
        logged_in = not user_sudo._is_public()
        # If the user is logged in, take their partner rather than the partner set in the params.
        # This is something that we want, since security rules are based on the partner, and created
        # tokens should not be assigned to the public user. This should have no impact on the
        # transaction itself besides making reconciliation possibly more difficult (e.g. The
        # transaction and invoice partners are different).
        partner_is_different = False
        # Overwrite for modify condition
        if logged_in and not partner_id:
            partner_is_different = partner_id and partner_id != user_sudo.partner_id.id
            partner_sudo = user_sudo.partner_id
        else:
            partner_sudo = request.env['res.partner'].sudo().browse(partner_id).exists()
            if not partner_sudo:
                return request.redirect(
                    # Escape special characters to avoid loosing original params when redirected
                    f'/web/login?redirect={urllib.parse.quote(request.httprequest.full_path)}'
                )

        # Instantiate transaction values to their default if not set in parameters
        reference = reference or payment_utils.singularize_reference_prefix(prefix='tx')
        amount = amount or 0.0  # If the amount is invalid, set it to 0 to stop the payment flow
        company_id = company_id or partner_sudo.company_id.id or user_sudo.company_id.id
        company = request.env['res.company'].sudo().browse(company_id)
        currency_id = currency_id or company.currency_id.id

        # Make sure that the currency exists and is active
        currency = request.env['res.currency'].browse(currency_id).exists()
        if not currency or not currency.active:
            raise werkzeug.exceptions.NotFound()  # The currency must exist and be active.

        # Select all providers and tokens that match the constraints
        providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            company_id, partner_sudo.id, amount, currency_id=currency.id, **kwargs
        )  # In sudo mode to read the fields of providers and partner (if not logged in)
        if provider_id in providers_sudo.ids:  # Only keep the desired provider if it's suitable
            providers_sudo = providers_sudo.browse(provider_id)
        payment_tokens = request.env['payment.token'].search(
            [('provider_id', 'in', providers_sudo.ids), ('partner_id', '=', partner_sudo.id)]
        ) if logged_in else request.env['payment.token']

        # Make sure that the partner's company matches the company passed as parameter.
        if not PaymentPortal._can_partner_pay_in_company(partner_sudo, company):
            providers_sudo = request.env['payment.provider'].sudo()
            payment_tokens = request.env['payment.token']

        # Compute the fees taken by providers supporting the feature
        fees_by_provider = {
            provider_sudo: provider_sudo._compute_fees(amount, currency, partner_sudo.country_id)
            for provider_sudo in providers_sudo.filtered('fees_active')
        }

        # Generate a new access token in case the partner id or the currency id was updated
        access_token = payment_utils.generate_access_token(partner_sudo.id, amount, currency.id)
        rendering_context = {
            'providers': providers_sudo,
            'tokens': payment_tokens,
            'fees_by_provider': fees_by_provider,
            'show_tokenize_input': self._compute_show_tokenize_input_mapping(
                providers_sudo, logged_in=logged_in, **kwargs
            ),
            'reference_prefix': reference,
            'amount': amount,
            'currency': currency,
            'partner_id': partner_sudo.id,
            'access_token': access_token,
            'transaction_route': '/payment/transaction',
            'landing_route': '/payment/confirmation',
            'res_company': company,  # Display the correct logo in a multi-company environment
            'partner_is_different': partner_is_different,
            **self._get_custom_rendering_context_values(**kwargs),
        }
        return request.render(self._get_payment_page_template_xmlid(**kwargs), rendering_context)