odoo.define('stride_payment_sales.FormView', function (require) {
"use strict";
    var Dialog = require('web.Dialog');

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');

    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;

    var StridePaymentSalesFormRenderer = FormRenderer.extend({
        /**
         * @override
         */
        start: async function () {
            await this._super.apply(this, arguments);
        },
    });

    var StridePaymentSalesFormController = FormController.extend({
        async _onButtonClicked(event){
            if (event.data.attrs.name === 'action_cancel_sale_payment'){
                window.location.reload();
            }
            if (event.data.attrs.name === 'action_register_sale_payment'){
                var payment_footer = document.getElementById('stride_sale_payment_footer');
                payment_footer.style.display = "none";
                var self = this;
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

                await self['processSalePayment' + event.data.record.data.provider_code](event);
                payment_footer.style.display = "";
            }
        },
    });

    var StridePaymentSalesFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: StridePaymentSalesFormController,
            Renderer: StridePaymentSalesFormRenderer,
        }),
    });

    viewRegistry.add('stride_sales_payments_popup', StridePaymentSalesFormView);
});