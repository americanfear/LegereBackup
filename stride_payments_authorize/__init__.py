from . import models

from odoo import api, SUPERUSER_ID

def _set_import_transactions_batch(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['payment.provider'].search([('code', '=', 'authorize')]).write({'import_transactions_batch': True})