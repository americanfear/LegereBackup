odoo.define('stride_payment_sales_authorize.FormView', function (require) {
"use strict";
    
    const { loadJS } = require('@web/core/assets');
    var Dialog = require('web.Dialog');
    var FormController = require('web.FormController');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;

    FormController.include({

        _getAuthorizePaymentDetails: function (event) {
            if (event.data.record.data.payment_method == 'card') {
                var cardNumber = event.data.record.data.authorize_card_number.replaceAll(' ', '');
                var cardCVV = event.data.record.data.authorize_card_cvc.trim();
                var cardExpMonth = event.data.record.data.authorize_card_expiry_month.replaceAll(' ', '');
                var cardExpYear = event.data.record.data.authorize_card_expiry_year.replaceAll(' ', '');
                return {
                    cardData: {
                        cardNumber: cardNumber.replace(/ /g, ''), // Remove all spaces
                        month: cardExpMonth,
                        year: cardExpYear,
                        cardCode: cardCVV,
                    },
                };
            } 

            if (event.data.record.data.payment_method == 'bank') {
                var nameOnAccount = event.data.record.data.authorize_name_on_account;
                var bankAccountNumber = event.data.record.data.authorize_account_number.trim();
                var bankRouting = event.data.record.data.authorize_aba_number.trim();
                var bankAccountType = event.data.record.data.authorize_account_type || 'checking';
                return {
                    bankData: {
                        nameOnAccount: nameOnAccount.substring(0, 22), // Max allowed by acceptjs
                        accountNumber: bankAccountNumber,
                        routingNumber: bankRouting,
                        accountType: bankAccountType,
                    },
                };
            }
        },

        authorizeResponseHandler: function (event, response) {
            var self = this;
            if (response.messages.resultCode === 'Error') {
                let error = "";
                response.messages.message.forEach(msg => error += `${msg.code}: ${msg.text}\n`);
                Dialog.alert(this, _t("We are not able to process your payment: \n") + error);
            }

            if (response.messages.resultCode === "Ok") {
                self._rpc({
                    model: 'stride.sale.payment',
                    method: 'process_card_payment',
                    context: event.data.record.context,
                    args: [
                        event.data.record.data.id,
                        response,
                        event.data.record.data.sale_order_id.data.id,
                        event.data.record.data.partner_id.data.id,
                        event.data.record.data.amount,
                        event.data.record.data.reference,
                        event.data.record.data.provider_id.data.id,
                        event.data.record.data.company_id.data.id,
                        event.data.record.data.currency_id.data.id,
                        event.data.record.data.send_receipt,
                        event.data.record.data.order_confirm,
                        event.data.record.data.create_downpayment,
                        event.data.record.data.auto_invoice,
                    ]
                }).then(function(data) {
                    window.location.reload();
                }).guardedCatch(function (error) {
                    // if the rpc fails, pretty obvious
                    error.event.preventDefault();
                    Dialog.alert(self, '', {
                        title: _t("Server error"),
                        $content: $('<div/>').html(
                            _t("We are not able to process your payment.")
                            + '<br/>'
                            + error.message.data.message
                        )
                    });
                });
            }
        },

        async processSalePaymentauthorize(event){
            var self = this;

            var providerState = event.data.record.data.provider_state;    
            let acceptJSUrl = 'https://js.authorize.net/v1/Accept.js';
            if (providerState !== 'enabled') {
                acceptJSUrl = 'https://jstest.authorize.net/v1/Accept.js';
            }

            try {
                await Promise.all([
                    new Promise(resolve => setTimeout(resolve, 3000)),
                    loadJS(acceptJSUrl)
                ]);
            } catch (error) {
                Dialog.alert(this, _t("We are not able to process your payment: \n") + error);
                return false;
            }

            if (event.data.record.data.payment_method == 'token') {
                self._rpc({
                    model: 'stride.sale.payment',
                    method: 'process_token_payment',
                    context: event.data.record.context,
                    args: [
                        event.data.record.data.id, 
                        event.data.record.data.sale_order_id.data.id,
                        event.data.record.data.partner_id.data.id,
                        event.data.record.data.amount,
                        event.data.record.data.reference,
                        event.data.record.data.payment_token_id.data.id,
                        event.data.record.data.provider_id.data.id,
                        event.data.record.data.company_id.data.id,
                        event.data.record.data.currency_id.data.id,
                        event.data.record.data.send_receipt,
                        event.data.record.data.order_confirm,
                        event.data.record.data.create_downpayment,
                        event.data.record.data.auto_invoice,
                    ]
                }).then(function(data) {
                    window.location.reload();
                }).guardedCatch(function (error) {
                    // if the rpc fails, pretty obvious
                    error.event.preventDefault();
                    Dialog.alert(self, '', {
                        title: _t("Server error"),
                        $content: $('<div/>').html(
                            _t("We are not able to process your payment.")
                            + '<br/>'
                            + error.message.data.message
                        )
                    });
                });
            }

            if (event.data.record.data.payment_method == 'card' || event.data.record.data.payment_method == 'bank') {
                var authorizeApiLoginID = event.data.record.data.authorize_login;
                var authorizeClientKey = event.data.record.data.authorize_client_key;
                
                if (event.data.record.data.payment_method == 'card') {
                    if (event.data.record.data.authorize_card_number == false || event.data.record.data.authorize_card_cvc == false || event.data.record.data.authorize_card_expires == false) {
                        Dialog.alert(self, '', {
                            title: _t("Validation error"),
                            $content: $('<div/>').html(
                                _t("Please enter card details.")
                            )
                        });
                        return false;
                    }
                    
                    // Build the authentication and card data objects to be dispatched to Authorized.Net
                    const secureData = {
                        authData: {
                            apiLoginID: authorizeApiLoginID,
                            clientKey: authorizeClientKey,
                        },
                        ...this._getAuthorizePaymentDetails(event),
                    };
                    // Dispatch secure data to Authorize.Net to get a payment nonce in return
                    return Accept.dispatchData(
                        secureData, response => self.authorizeResponseHandler(event, response)
                    );
                } else {
                    if (event.data.record.data.authorize_name_on_account == false || event.data.record.data.authorize_account_number == false || event.data.record.data.authorize_aba_number == false) {
                        Dialog.alert(self, '', {
                            title: _t("Validation error"),
                            $content: $('<div/>').html(
                                _t("Please enter bank details.")
                            )
                        });
                        return false;
                    }
                    
                    // Build the authentication and card data objects to be dispatched to Authorized.Net
                    const secureData = {
                        authData: {
                            apiLoginID: authorizeApiLoginID,
                            clientKey: authorizeClientKey,
                        },
                        ...this._getAuthorizePaymentDetails(event),
                    };

                    // Dispatch secure data to Authorize.Net to get a payment nonce in return
                    return Accept.dispatchData(
                        secureData, response => self.authorizeResponseHandler(event, response)
                    );
                }
            }
        },
    });
});