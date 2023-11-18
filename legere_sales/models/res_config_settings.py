from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_invoice_clearing_account_id = fields.Many2one('account.account', string='Clearing Account')
    olympia_fiscal_id = fields.Many2one('account.fiscal.position', string='Olympia Fiscal')

    

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_invoice_clearing_account_id = fields.Many2one('account.account', string='Clearing Account', related='company_id.auto_invoice_clearing_account_id', store=True, readonly=False)
    olympia_fiscal_id = fields.Many2one('account.fiscal.position', string='Olympia Fiscal', related='company_id.olympia_fiscal_id', store=True, readonly=False)