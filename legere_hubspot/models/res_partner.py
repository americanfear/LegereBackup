from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    hubspot_id = fields.Char(string='Hubspot ID')
    hubspot_state = fields.Char(string='Hubspot State')

    def write(self, vals):
        if vals.get('hubspot_state'):
            state_id = self.env['res.country.state'].sudo().search([('code', '=', vals.get('hubspot_state'))], limit=1)
            if state_id:
                vals.update({'state_id': state_id.id})
        return super(ResPartner, self).write(vals)