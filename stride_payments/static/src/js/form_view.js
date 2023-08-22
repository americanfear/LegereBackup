odoo.define('stride_payments.FormView', function (require) {
"use strict";
    var Dialog = require('web.Dialog');

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');

    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;

    var StridePaymentsFormRenderer = FormRenderer.extend({
        /**
         * @override
         */
        start: async function () {
            await this._super.apply(this, arguments);
        },
    });

    var StridePaymentsFormController = FormController.extend({
        async _onButtonClicked(event){
            if (event.data.attrs.name === 'action_cancel_invoice_payment'){
                window.location.reload();
            }
            if (event.data.attrs.name === 'action_register_invoice_payment'){
                var self = this;
                var payment_footer = document.getElementById('stride_invoice_payment_footer');
                payment_footer.style.display = "none";
                if (event.data.record.data.provider_id == false) {
                    payment_footer.style.display = "";
                    Dialog.alert(self, '', {
                        title: _t("Validation error"),
                        $content: $('<div/>').html(
                            _t("Please select payment provider.")
                        )
                    });
                    return false;
                }

                if (event.data.record.data.send_receipt == true && event.data.record.data.partner_email == false){
                    payment_footer.style.display = "";
                    Dialog.alert(self, '', {
                        title: _t("Validation error"),
                        $content: $('<div/>').html(
                            _t("If you wants to send receipt please set email address on partner.")
                        )
                    });
                    return false;
                }

                if (event.data.record.data.payment_method == 'token' && event.data.record.data.payment_token_id == false) {
                    payment_footer.style.display = "";
                    Dialog.alert(self, '', {
                        title: _t("Validation error"),
                        $content: $('<div/>').html(
                            _t("Please select saved payment token.")
                        )
                    });
                    return false;
                }

                if (event.data.record.data.provider_code == 'payengine') {
                    await self.processPaymentpayengine(event);
                    payment_footer.style.display = "";  
                }

                if (event.data.record.data.provider_code == 'stride') {
                    await self.processPaymentstride(event);
                    payment_footer.style.display = ""; 
                }
            }
        },
    });

    var StridePaymentsFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: StridePaymentsFormController,
            Renderer: StridePaymentsFormRenderer,
        }),
    });

    viewRegistry.add('stride_payments_popup', StridePaymentsFormView);
});