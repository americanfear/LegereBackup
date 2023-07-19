import logging
import pprint

from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _, api, fields, models,_

_logger = logging.getLogger(__name__)

class StrideSalePayment(models.Model):
    _inherit = 'stride.sale.payment'
    _description = 'Stride Sale Payment'

    authorize_card_number = fields.Char(string='Card Number')
    authorize_card_expiry_month = fields.Char(string='Expiry(MM)')
    authorize_card_expiry_year = fields.Char(string='Expiry(YY)')
    authorize_card_cvc = fields.Char(string='CVC')
    authorize_name_on_account = fields.Char(string='Name On Account')
    authorize_account_number = fields.Char(string='Account Number')
    authorize_aba_number = fields.Char(string='ABA Routing Number')
    authorize_account_type = fields.Selection([('checking', 'Personal Checking'),
        ('savings', 'Personal Savings')], default='checking', string='Bank Account Type')
    authorize_login = fields.Char(
        string="Authorize API Login ID", related="provider_id.authorize_login")
    authorize_client_key = fields.Char(
        string="Authorize API Client Key", related="provider_id.authorize_client_key")

    def authorize_process_token_payment(self, order_id, partner_id, amount, reference, payment_token_id, provider_id, company_id, currency_id, send_receipt, invoice):
        try:
            stride_sale_payment_pool = self.env['stride.sale.payment']
            payment_token = self.env['payment.token'].browse(payment_token_id)
            if not payment_token.authorize_profile:
                raise UserError("Authorize.Net: " + _("The transaction is not linked to a token."))
            tx = stride_sale_payment_pool.create_payment_transaction(order_id=order_id, partner_id=partner_id, amount=amount, reference=reference, payment_token_id=payment_token_id, provider_id=provider_id, company_id=company_id, currency_id=currency_id, invoice=invoice)
            payment_provider_id = self.env['payment.provider'].browse(provider_id)

            #Process Payment
            authorize_API = AuthorizeAPI(payment_provider_id)
            res_content = {}
            if payment_provider_id.capture_manually:
                res_content = authorize_API.authorize(tx, token=payment_token)
                _logger.info(
                    "authorize request response for transaction with reference %s:\n%s",
                    tx.reference, pprint.pformat(res_content)
                )
            else:
                res_content = authorize_API.auth_and_capture(tx, token=payment_token)
                _logger.info(
                    "auth_and_capture request response for transaction with reference %s:\n%s",
                    tx.reference, pprint.pformat(res_content)
                )
            if res_content and res_content.get('x_response_reason_text'):
                raise AccessError(_('%s.' %(res_content.get('x_response_reason_text'))))
            tx._handle_notification_data('authorize', {'response': res_content})

            #Create account payment and reconcile with invoice
            if tx.state == 'done':
                account_payment_id = stride_sale_payment_pool.create_account_payment(partner_id=partner_id, amount=amount, reference=reference, payment_token_id=payment_token_id, provider_id=provider_id, company_id=company_id, currency_id=currency_id, payment_transaction_id=tx)
                tx.write({'payment_id': account_payment_id.id, 'is_post_processed': True})
                account_payment_id.action_post()
            
                if invoice:
                    domain = [
                        ('parent_state', '=', 'posted'),
                        ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                        ('reconciled', '=', False),
                    ]
                    payment_lines = account_payment_id.line_ids.filtered_domain(domain)
                    lines = invoice.mapped('line_ids')
                    for account in payment_lines.account_id:
                        (payment_lines + lines)\
                            .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                            .reconcile()

                if send_receipt:
                    stride_sale_payment_pool.action_send_receipt(payment_id=account_payment_id)
        except Exception as e:
            raise AccessError(_('%s.' %(str(e))))

    def authorize_process_card_payment(self, response, order_id, partner_id, amount, reference, provider_id, company_id, currency_id, send_receipt, invoice):
        try:
            stride_sale_payment_pool = self.env['stride.sale.payment']
            tx = stride_sale_payment_pool.create_payment_transaction(order_id=order_id, partner_id=partner_id, amount=amount, reference=reference, payment_token_id=False, provider_id=provider_id, company_id=company_id, currency_id=currency_id, invoice=invoice)
            payment_provider_id = self.env['payment.provider'].browse(provider_id)

            #Process Payment
            authorize_API = AuthorizeAPI(payment_provider_id)
            response_content = {}
            if payment_provider_id.capture_manually or tx.operation == 'validation':
                response_content = authorize_API.authorize(tx, opaque_data=response.get('opaqueData'))
                _logger.info(
                    "authorize request response for transaction with reference %s:\n%s",
                    tx.reference, pprint.pformat(response_content)
                )
            else:
                response_content = authorize_API.auth_and_capture(tx, opaque_data=response.get('opaqueData'))
                _logger.info(
                    "auth_and_capture request response for transaction with reference %s:\n%s",
                    tx.reference, pprint.pformat(response_content)
                )
            if response_content and response_content.get('x_response_reason_text'):
                raise AccessError(_('%s.' %(response_content.get('x_response_reason_text'))))
            tx._handle_notification_data('authorize', {'response': response_content})

            #Create account payment and reconcile with invoice
            if tx.state == 'done':
                account_payment_id = stride_sale_payment_pool.create_account_payment(partner_id=partner_id, amount=amount, reference=reference, payment_token_id=False, provider_id=provider_id, company_id=company_id, currency_id=currency_id, payment_transaction_id=tx)
                tx.write({'payment_id': account_payment_id.id, 'is_post_processed': True})
                account_payment_id.action_post()
            
                if invoice:
                    domain = [
                        ('parent_state', '=', 'posted'),
                        ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                        ('reconciled', '=', False),
                    ]
                    payment_lines = account_payment_id.line_ids.filtered_domain(domain)
                    lines = invoice.mapped('line_ids')
                    for account in payment_lines.account_id:
                        (payment_lines + lines)\
                            .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                            .reconcile()

                if send_receipt:
                    stride_sale_payment_pool.action_send_receipt(payment_id=account_payment_id)
        except Exception as e:
            raise AccessError(_('%s.' %(str(e))))