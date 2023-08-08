{
    'name': 'Legere Custom',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'summary': """generic module""",
    'description': """
        generic module
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['sale_management', 'stock', 'purchase', 'mrp', 'hr_expense'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}