{
    'name': 'Custom Services Flow',
    'version': '1.0',
    'category': 'Sales/Sales',
    'summary': """Service Flow for the sale and project""",
    'description': """Service Flow for the sale and project""",
    'license': 'Other proprietary',
    'author': 'Dream Mountain Services',
    'website': 'https://DreamMtn.Services',
    'support': 'support@DreamMtn.Services',   
    'depends': ['sale_management', 'project', 'mrp'],
    'data': [
        'views/sale_order_views.xml',
        'views/res_config_settings_view.xml',
        'views/project_views.xml',        
        'views/product_template_view.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}