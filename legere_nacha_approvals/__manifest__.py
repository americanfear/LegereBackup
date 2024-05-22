{
    'name': 'Legere NACHA Approvals',
    'version': '1.0',
    "category": "Accounting/Accounting",
    'summary': """Implemented Approval Flow for NACHA Payments""",
    'description': """Implemented Approval Flow for NACHA Payments""",
    'license': 'OPL-1',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    "depends": ["stride_billpay", "l10n_us_payment_nacha"],
    'data': [
        'data/mail_template_data.xml',
        'views/account_batch_payment_views.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}