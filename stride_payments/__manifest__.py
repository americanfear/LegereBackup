{
    'name': 'Stride: Payment',
    'version': '16.0.1.0.1',
    'category': 'Accounting/Payment',
    'summary': """Stride Payment""",
    'description': """Stride Payment""",
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['payment', 'account', 'stride_payment_token'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/cron_data.xml',
        'wizard/stride_payment_transaction_refund_views.xml',
        'wizard/stride_invoice_payment_views.xml',
        'views/payment_transaction_views.xml',
        'views/account_payment_view.xml',
        'views/payment_transactions_batch_views.xml',
        'views/payment_templates.xml',
        'views/payment_provider_views.xml'

    ],
    'assets': {
        'web.assets_backend': [
            'stride_payments/static/src/js/form_view.js',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,

}