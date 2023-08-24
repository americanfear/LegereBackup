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
    
    'depends': ['sale_management', 'sale_stock', 'purchase', 'sale_mrp', 'hr_expense', 'sale_project'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/project_task_views.xml',
        'views/stock_picking_views.xml',
        'views/mrp_production_views.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}