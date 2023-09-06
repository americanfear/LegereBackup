{
    'name': 'Legere Account Followup',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': """customization related to account followup module""",
    'description': """
        customization related to account followup module
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['account_followup'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}