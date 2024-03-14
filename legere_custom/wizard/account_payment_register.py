from odoo import models, fields, api, _

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    available_journal_ids = fields.Many2many(comodel_name='account.journal',
        compute='_compute_available_journal_ids'
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True, readonly=False, precompute=True,
        domain="[('id', 'in', available_journal_ids)]")

    @api.depends('available_journal_ids')
    def _compute_journal_id(self):
        super(AccountPaymentRegister, self)._compute_journal_id()
        for wizard in self.filtered(lambda x: x.amount == 0.0):
            wizard.journal_id = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', wizard.company_id.id),
                ('id', 'in', self.available_journal_ids.ids)
            ], limit=1)

    @api.depends('payment_type', 'company_id', 'can_edit_wizard', 'amount')
    def _compute_available_journal_ids(self):
        for wizard in self:
            if wizard.can_edit_wizard and wizard.amount != 0.0:
                batch = wizard._get_batches()[0]
                wizard.available_journal_ids = wizard._get_batch_available_journals(batch)
            else:
                wizard.available_journal_ids = self.env['account.journal'].search([
                    ('company_id', '=', wizard.company_id.id),
                    ('type', 'in', ('bank', 'cash', 'general')),
                ])

    @api.depends('early_payment_discount_mode', 'amount')
    def _compute_payment_difference_handling(self):
        super(AccountPaymentRegister, self)._compute_payment_difference_handling()
        for wizard in self.filtered(lambda x: x.amount == 0.0):
            wizard.payment_difference_handling = 'reconcile'