{
    'name': 'Legere Stock',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'summary': """customization related to stock module""",
    'description': """
        customization related to stock module
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['stock'],
    'data': [
        'views/report_stockpicking_operations.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}