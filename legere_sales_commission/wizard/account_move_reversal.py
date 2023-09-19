from odoo import models, fields, api

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super(AccountMoveReversal, self)._prepare_default_reversal(move=move)
        res.update({'is_new_customer': move.is_new_customer})
        return res