{
    'name': 'Stride: Package Consume',
    'version': '16.0.1.0.0',
    'category': 'Inventory/Inventory',
    'sequence': 1,
    'summary': """create material moves for product packaging.""",
    'description': """create material moves for product packaging.""",
    'license': 'Other proprietary',
    'author': 'Dream Mountain Services',
    'website': 'https://DreamMtn.Services',
    'support': 'support@DreamMtn.Services',   
    'depends': ['stock', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_packaging_views.xml',
        'views/stock_picking_views.xml',
    ],
   
    'application': True,
    'installable': True,
    'auto_install': False,
}