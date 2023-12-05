from odoo import _, api, fields, models

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'authorize').update({
            'support_manual_capture': True,
            'support_refund': 'partial',
            'support_tokenization': True,
        })