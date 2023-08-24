{
    'name': 'Stride: Billpay',
    'version': '1.0',
    "category": "Accounting/Accounting",
    'summary': """Billpay""",
    'description': """Billpay""",
    'license': 'OPL-1',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    "depends": ["payment", "account"],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_approval_views.xml',
        'wizard/payment_approval_reject_reason_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}