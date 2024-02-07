import logging
import pprint
import ast

from odoo import _, models, fields
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI
from odoo.addons.payment_authorize.const import TRANSACTION_STATUS_MAPPING


_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    authorize_account_type = fields.Char(string='Authorize Account Type')
    
    def _send_refund_request(self, amount_to_refund=None):
        """ Override of payment to send a refund request to Authorize.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        self.ensure_one()

        if self.provider_code != 'authorize':
            return super()._send_refund_request(amount_to_refund=amount_to_refund)

        authorize_api = AuthorizeAPI(self.provider_id)
        tx_details = authorize_api.get_transaction_details(self.provider_reference)
        if 'err_code' in tx_details:  # Could not retrieve the transaction details.
            raise ValidationError("Authorize.Net: " + _(
                "Could not retrieve the transaction details. (error code: %s; error_details: %s)",
                tx_details['err_code'], tx_details.get('err_msg')
            ))

        refund_tx = self.env['payment.transaction']
        tx_status = tx_details.get('transaction', {}).get('transactionStatus')
        if tx_status in TRANSACTION_STATUS_MAPPING['voided']:
            # The payment has been voided from Authorize.net side before we could refund it.
            self._set_canceled()
        elif tx_status in TRANSACTION_STATUS_MAPPING['refunded']:
            # The payment has been refunded from Authorize.net side before we could refund it. We
            # create a refund tx on Odoo to reflect the move of the funds.
            refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
            refund_tx._set_done()
            # Immediately post-process the transaction as the post-processing will not be
            # triggered by a customer browsing the transaction from the portal.
            self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif any(tx_status in TRANSACTION_STATUS_MAPPING[k] for k in ('authorized', 'captured')):
            if tx_status in TRANSACTION_STATUS_MAPPING['authorized']:
                rounded_amount = round(amount_to_refund, self.currency_id.decimal_places)
                amount_to_process = (self.amount - abs(rounded_amount))
                if amount_to_process > 0.0 and not self.token_id:
                    raise ValidationError(_('Partial Refund:\nThe payment has not yet been finalized on the Authorize.net side. Please await the completion of the payment settlement process.'))  
                
                # The payment has not been settle on Authorize.net yet. It must be voided rather
                # than refunded. Since the funds have not moved yet, we don't create a refund tx.
                res_content = authorize_api.void(self.provider_reference)
                tx_to_process = self
            
                if amount_to_process > 0.0:
                    reference = self.env['payment.transaction'].sudo()._compute_reference(
                        self.token_id.provider_id.code,
                        prefix=self.reference
                    )
                    new_tx = self.env['payment.transaction'].sudo().create({
                        'provider_id': self.provider_id.id,
                        'reference': reference,
                        'amount': amount_to_process,
                        'currency_id': self.currency_id.id,
                        'partner_id': self.partner_id.id,
                        'token_id': self.token_id.id,
                        'tokenize': False
                    })

                    # response_content = new_tx._authorize_create_transaction_request(ast.literal_eval(self.opaque_data))
                    # new_tx._handle_notification_data('authorize', {'response': response_content})
                    if self.provider_id.capture_manually:
                        new_res_content = authorize_api.authorize(new_tx, token=self.token_id)
                        _logger.info(
                            "authorize request response for transaction with reference %s:\n%s",
                            new_tx.reference, pprint.pformat(new_res_content)
                        )
                    else:
                        new_res_content = authorize_api.auth_and_capture(new_tx, token=self.token_id)
                        _logger.info(
                            "auth_and_capture request response for transaction with reference %s:\n%s",
                            new_tx.reference, pprint.pformat(new_res_content)
                        )
                    new_tx._process_notification_data({'response': new_res_content})
                    new_tx._execute_callback()
                    #new_tx._handle_notification_data('authorize', {'response': new_res_content})

                    if self.sale_order_ids or self.invoice_ids:
                        new_tx.write({
                            'sale_order_ids': [(6, 0, self.sale_order_ids.ids)],
                            'invoice_ids': [(6, 0, self.invoice_ids.ids)],
                        })
            else:
                # The payment has been settled on Authorize.net side. We can refund it.
                refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
                rounded_amount = round(amount_to_refund, self.currency_id.decimal_places)
                res_content = authorize_api.refund(
                    self.provider_reference, rounded_amount, tx_details
                )
                tx_to_process = refund_tx
            _logger.info(
                "refund request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(res_content)
            )
            data = {'reference': tx_to_process.reference, 'response': res_content}
            tx_to_process._handle_notification_data('authorize', data)
        else:
            raise ValidationError("Authorize.net: " + _(
                "The transaction is not in a status to be refunded. (status: %s, details: %s)",
                tx_status, tx_details.get('messages', {}).get('message')
            ))
        return refund_tx