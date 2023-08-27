import logging
import pprint
import requests
import json
import pytz
from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from datetime import datetime

_logger = logging.getLogger(__name__)

class PaymentTransactionsBatch(models.Model):
    _inherit = 'payment.transactions.batch'

    @api.model
    def authorize_import_payment_transactions_batch(self, record=False):
        try:
            payment_transactions_batch_pool = self.env['payment.transactions.batch']
            payment_transaction_pool = self.env['payment.transaction']
            from_date = fields.Date.today() - relativedelta(days=3) #requesting a few days back for redundancy, in case a cron fails or they post late)
            to_date = fields.Date.today()

            if record.state == 'enabled':
                url = 'https://api.authorize.net/xml/v1/request.api'
            else:
                url = 'https://apitest.authorize.net/xml/v1/request.api'
            
            values = {
                'getSettledBatchListRequest': {
                    'merchantAuthentication': {
                        'name': record.authorize_login,
                        'transactionKey': record.authorize_transaction_key
                    },
                    'firstSettlementDate': fields.Date.to_string(from_date) + 'T00:00:00',
                    'lastSettlementDate': fields.Date.to_string(to_date) + 'T23:59:59'
                }
            }

            _logger.info("Authorize Batch: sending request to %s:\n%s", url, pprint.pformat(values))

            response = requests.post(url, json.dumps(values), timeout=60)
            response = json.loads(response.content)
            _logger.info("response received:\n%s", pprint.pformat(response))

            if response.get('messages') and response.get('messages').get('resultCode') == 'Ok':
                for batch in response.get('batchList', []):
                    batch_id = payment_transactions_batch_pool.search([('BatchNumber', '=', batch.get('batchId')),
                        ('company_id', '=', record.company_id.id),
                        ('payment_provider_id', '=', record.id)], limit=1)
                    if not batch_id:
                        batch_id = payment_transactions_batch_pool.create({'BatchNumber': batch.get('batchId'),
                                'company_id': record.company_id.id,
                                'payment_provider_id': record.id
                            })
                        #only create batch if it doesn't already exist, batches should never be changed after they are created, so we can skip them.
                        if batch.get('settlementTimeUTC'):
                            batch_date = batch.get('settlementTimeUTC').split('T')[0]
                            batch_id.write({'SubmitDate': datetime.strptime(batch_date, '%Y-%m-%d')})


                        values = {
                            'getTransactionListRequest': {
                                'merchantAuthentication': {
                                    'name': record.authorize_login,
                                    'transactionKey': record.authorize_transaction_key
                                },
                                'batchId': batch.get('batchId')
                            }
                        }

                        _logger.info("Authorize Transaction: sending request to %s:\n%s", url, pprint.pformat(values))

                        response = requests.post(url, json.dumps(values), timeout=60)
                        response = json.loads(response.content)
                        _logger.info("response received:\n%s", pprint.pformat(response))

                        for transaction in response.get('transactions', []):
                            if transaction.get('transactionStatus') in ['settledSuccessfully']:
                                transaction_id = payment_transactions_batch_pool.check_payment_transaction(transaction_ID=transaction.get('transId'), batch_id=batch_id)
                                if not transaction_id:
                                    payment_transaction_pool.create({'provider_id': record.id,
                                        'amount': float(transaction.get('settleAmount')),
                                        'currency_id': record.company_id.currency_id.id,
                                        'partner_id': record.company_id.partner_id.id,
                                        'reference': transaction.get('transId'),
                                        'provider_reference': transaction.get('transId'),
                                        'payment_transactions_batch_id': batch_id.id,
                                        'is_post_processed': True,
                                        'state': 'done',
                                        'authorize_account_type': transaction.get('accountType'),
                                    })
        except Exception as e:
            _logger.info("%s", str(e))

    def action_create_bank_statement(self):
        account_bank_statement_line_pool = self.env['account.bank.statement.line']
        for record in self:
            if record.payment_provider_id and record.payment_provider_id.code == 'authorize':
                journal_id = record.payment_transaction_ids.filtered(lambda x: x.provider_id)[0].provider_id.journal_id 
                account_bank_statement_id = self.env['account.bank.statement'].create({'date': record.SubmitDate and record.SubmitDate.date() or fields.Date.today(),
                    'name': "batch_"+record.BatchNumber+"_statement",
                    'journal_id': journal_id.id,
                    'balance_start': 0.0,
                    'balance_end_real': 0.0})
                
                amount_without_payment = sum(record.payment_transaction_ids.filtered(lambda x: not x.payment_id).mapped('amount'))
                amount_without_payment_des = ', '.join([o.reference for o in record.payment_transaction_ids.filtered(lambda x: not x.payment_id)])
                SubmitDate_tz = pytz.utc.localize(record.SubmitDate).astimezone(pytz.timezone(self.env.user.tz or 'UTC')) if record.SubmitDate else False
                if amount_without_payment > 0.0:
                    account_bank_statement_line_pool.create({'date': SubmitDate_tz and SubmitDate_tz.date() or fields.Date.today(),
                        'journal_id': journal_id.id,
                        'partner_id': False,
                        'payment_ref': amount_without_payment_des,
                        'statement_id': account_bank_statement_id.id,
                        'amount': amount_without_payment})
                
                for payment_transaction in record.payment_transaction_ids.filtered(lambda x: x.payment_id):
                    account_bank_statement_line_pool.create({'date': payment_transaction.last_state_change.date(),
                        'journal_id': journal_id.id,
                        'partner_id': payment_transaction.partner_id.id,
                        'payment_ref': payment_transaction.reference,
                        'statement_id': account_bank_statement_id.id,
                        'amount': payment_transaction.amount})


                american_express_amount = sum(record.payment_transaction_ids.filtered(lambda x: x.authorize_account_type == 'American Express').mapped('amount'))
                if american_express_amount != 0.0:
                    account_bank_statement_line_pool.create({'date': SubmitDate_tz and SubmitDate_tz.date() or fields.Date.today(),
                        'journal_id': journal_id.id,
                        'partner_id': False,
                        'payment_ref': 'Transfer (American Express)',
                        'statement_id': account_bank_statement_id.id,
                        'amount': -american_express_amount})

                non_american_express_amount = sum(record.payment_transaction_ids.filtered(lambda x: x.authorize_account_type != 'American Express').mapped('amount'))
                if non_american_express_amount != 0.0:
                    account_bank_statement_line_pool.create({'date': SubmitDate_tz and SubmitDate_tz.date() or fields.Date.today(),
                        'journal_id': journal_id.id,
                        'partner_id': False,
                        'payment_ref': 'Transfer (Other)',
                        'statement_id': account_bank_statement_id.id,
                        'amount': -non_american_express_amount})

                record.write({'account_bank_statement_id': account_bank_statement_id.id})
            else:
                return super(PaymentTransactionsBatch, self).action_create_bank_statement()