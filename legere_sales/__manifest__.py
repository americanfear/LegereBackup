{
    'name': 'Legere Sales',
    'version': '1.0',
    'category': 'Sales/Sales',
    'summary': """Legere Sales""",
    'description': """
        Legere Sales
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['sale_management', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/project_task_views.xml',
        'wizard/check_and_confirm_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}