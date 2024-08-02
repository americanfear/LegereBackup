{
    'name': 'Stride: Payment Authorize - Enterprise',
    'version': '16.0.1.0.2',
    'category': 'Accounting/Payment Providers',
    'summary': """stride payment authorize""",
    'description': """stride payment sales authorize""",
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['stride_payments_statements_ee', 'payment_authorize'],
    'data': [
    ],
    'post_init_hook': '_set_import_transactions_batch',
    'application': True,
    'installable': True,
    'auto_install': False,
}