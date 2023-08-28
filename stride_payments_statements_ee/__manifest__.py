{
    'name': 'Stride: Transaction Batch to Statements - Enterprise',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Payment Acquirers',
    'summary': """Transaction Batch to Statements""",
    'description': """Transaction Batch to Statements""",
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['stride_payments'],
    'data': [
        'data/cron.xml',
        'views/payment_transactions_batch_views.xml',
    ],
    
    'installable': True,
    'application': False,
    'auto_install': False,

}