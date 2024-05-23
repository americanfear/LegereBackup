{
    'name': 'Legere NACHA Approvals',
    'version': '1.1',
    "category": "Accounting/Accounting",
    'summary': """Implemented Approval Flow for NACHA Payments""",
    'description': """Implemented Approval Flow for NACHA Payments""",
    'license': 'OPL-1',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    "depends": ["l10n_us_payment_nacha"],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/account_approver_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}