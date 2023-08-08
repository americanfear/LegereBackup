from . import models
from . import controllers
from . import wizard

from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    data_id = env['ir.model.data'].search([('module', '=', 'stock'),
    	('name', '=', 'mail_template_data_delivery_confirmation')], limit=1)
    if data_id:
    	data_id.sudo().write({'noupdate': False})