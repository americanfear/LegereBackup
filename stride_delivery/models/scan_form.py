import easypost
import time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import except_orm, UserError

class EasypostScanForm(models.Model):
    _name = 'easypost.scan.form'
    _inherit = ['mail.thread']
    _description = "New scan form"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'easypost.scan.form') or _("New")

        return super(EasypostScanForm, self).create(vals_list)

    def _get_default_start_date(self):
        start_date = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        return start_date - relativedelta(hours=5, minutes=30)

    name = fields.Char(
        string="Name",
        required=True, copy=False, readonly=True,
        index='trigram',
        default=lambda self: _('New'))
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('fail', 'Failed'), ('done', 'Done')], default="draft")
    start_date = fields.Datetime('Start Date', default=_get_default_start_date)
    end_date = fields.Datetime('End Date', default=lambda self: fields.Datetime.now())
    shipping_ids = fields.Many2many('easypost.shipment', string='Shipments', copy=False)
    batch_id = fields.Char('Batch', copy=False)
    scann_form_id = fields.Char('Scan Form')
    easypost_carrier_id = fields.Many2one('easypost.carrier', string='Carrier')
    is_shipments = fields.Boolean(copy=False)
    form_url = fields.Char()
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    attachment_ids = fields.Many2many('ir.attachment', domain=lambda self: [('res_model', '=', self._name)], auto_join=True, string='Attachments')

    def get_shipments(self):
        shippings = self.env['easypost.shipment'].search(['&','&',
                                                ('create_date', '>=', self.start_date), 
                                                ('create_date', '<=', self.end_date), 
                                                '|',
                                                ('scan_form_status', '=', 'waiting'),
                                                ('scan_form_status', '=', False)                                                  
                                                ])
        shipping_ids = []
        for shipping in shippings:
            shipping_carrier = shipping.picking_id.carrier_id.easypost_carrier_id
            if shipping_carrier == self.easypost_carrier_id:
                shipping_ids.append(shipping.id)        
        
        if shipping_ids:
            self.shipping_ids = shipping_ids
            self.is_shipments = True
        else:
            raise UserError(_('No Shipments Found For these Conditions'))

    def confirm_data(self):
        self.state = 'confirm'

    def generate_batch(self):
        prod_environment = self.company_id.scanform_prod_environment
        easypost.api_key = self.company_id._get_easypost_api_key(prod_environment)
        try:
            shipping_list = []
            for shipping in self.shipping_ids:
                shipping_list.append(shipping.shipping_id)
            scan_form = easypost.ScanForm.create(shipments=shipping_list)
            while scan_form.status == "creating":
                time.sleep(5)
                scan_form.refresh()
            if scan_form.status == 'failed':
                self.state = 'fail'
            else:
                for shipping in self.shipping_ids:
                    shipping.is_scan_form = True
                self.env['ir.attachment'].create({'name': 'Postage Label',
                                                  'type': 'url',
                                                  'url': scan_form.get('form_url'),
                                                  'res_model': 'easypost.scan.form',
                                                  'res_id': self.id
                                                })
                self.write({'form_url': scan_form.get('form_url'),
                            'scann_form_id': scan_form.get('id'),
                            'batch_id': scan_form.get('batch_id'),
                            'state': 'done',
                            })
        except Exception as e:
            raise except_orm(('Error!'), str(e))

    def get_scan_form(self):
        for form in self:
            self.env['ir.attachment'].create({'name': 'Postage Label', 'type': 'url', 'url': form.form_url,
                 'res_model': 'easypost.scan.form', 'res_id': form.id})