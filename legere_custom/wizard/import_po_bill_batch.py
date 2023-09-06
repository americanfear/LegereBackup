import csv
import logging
import base64

from io import StringIO, BytesIO
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class ImportPurchaseBillBatch(models.TransientModel):
    _name = 'import.po.bill.batch'
    _description = 'Import Purchase Bill Batch'

    csv_file = fields.Binary('CSV File', required=True)

    def do_action(self):
        po_bill_batch_pool = self.env['po.bill.batch']
        missing_order_pool = self.env['po.bill.batch.missing.order']
        shipping_cost_pool = self.env['po.bill.batch.shipping.cost']
        purchase_order_pool = self.env['purchase.order']
        import_file = BytesIO(base64.decodebytes(self.csv_file))
        file_read = StringIO(import_file.read().decode())
        csv_data = csv.DictReader(file_read, delimiter=",")
        batch_id = False
        shipping_items = self.env.company.shipping_items
        for data in csv_data:
            if not batch_id:
                batch_id = po_bill_batch_pool.create({
                    'name': 'New'
                })
            if data.get('Item') and data.get('Item') in shipping_items:
                shipping_cost_pool.create({
                    'name': data.get('Item'),
                    'amount': data.get('Amount') and float(data.get('Amount')) or 0.0,
                    'po_bill_batch_id': batch_id.id,
                })
            else:
                if data.get('P.O.#'):
                    if '/' in data.get('P.O.#'):
                        order_refs = data.get('P.O.#').split('/')
                        for order_ref in order_refs:
                            purchase_order = purchase_order_pool.search([('origin', '=', order_ref)], limit=1)      
                            if purchase_order:
                                purchase_order.write({'po_bill_batch_id': batch_id.id})
                            else:
                                missing_order_pool.create({
                                    'name': data,
                                    'po_bill_batch_id': batch_id.id
                                })
                    else:
                        purchase_order = purchase_order_pool.search([('origin', '=', data.get('P.O.#'))], limit=1)
                        if purchase_order:
                            purchase_order.write({'po_bill_batch_id': batch_id.id})
                        else:
                            missing_order_pool.create({
                                'name': data,
                                'po_bill_batch_id': batch_id.id
                            })
        if batch_id:
            form_view = [(self.env.ref('legere_custom.view_po_bill_batch_form').id, 'form')]
            action = self.env['ir.actions.act_window']._for_xml_id('legere_custom.action_po_bill_batch_form')
            action['res_id'] = batch_id.id
            action['views'] = form_view
            return action