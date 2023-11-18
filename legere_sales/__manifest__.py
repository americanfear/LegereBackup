{
    'name': 'Legere Sales',
    'version': '1.0.1',
    'category': 'Sales/Sales',
    'summary': """customization related to sales module""",
    'description': """
        customization related to sales module
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['sale_management', 'project', 'sale_stock', 'purchase_stock', 'stock_dropshipping'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/project_task_views.xml',
        'views/res_config_setting_views.xml',
        'wizard/check_and_confirm_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}