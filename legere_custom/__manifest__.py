{
    'name': 'Legere Custom',
    'version': '1.0.3',
    'category': 'Inventory/Inventory',
    'summary': """generic module""",
    'description': """
        generic module
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['sale_management', 'sale_stock', 'purchase', 'sale_mrp', 'hr_expense', 'sale_project', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'wizard/import_po_bill_batch_views.xml',
        'wizard/account_payment_register_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/project_task_views.xml',
        'views/stock_picking_views.xml',
        'views/mrp_production_views.xml',
        'views/po_bill_batch_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}