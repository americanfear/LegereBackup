import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _cron_execute_followup_company(self):
        followup_data = self._query_followup_data(all_partners=True)
        in_need_of_action = self.env['res.partner'].browse([d['partner_id'] for d in followup_data.values() if d['followup_status'] == 'in_need_of_action'])
        #Overwrite method for filter based on payment term
        in_need_of_action_auto = in_need_of_action.filtered(lambda p: p.followup_line_id.auto_execute and p.followup_reminder_type == 'automatic' and p.property_payment_term_id)
        for partner in in_need_of_action_auto:
            try:
                partner._execute_followup_partner()
            except UserError as e:
                # followup may raise exception due to configuration issues
                # i.e. partner missing email
                _logger.warning(e, exc_info=True)

    def action_manually_process_automatic_followups(self):
        for partner in self.filtered(lambda x: x.property_payment_term_id):
            partner._execute_followup_partner()