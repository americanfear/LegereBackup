{
    'name': 'Legere Sales Commission',
    'version': '1.0.1',
    'category': 'Sales/Sales',
    'summary': """calculating sales person commission""",
    'description': """
        calculating sales person commission
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/security_rule.xml',
        'data/cron.xml',
        'views/commission_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}