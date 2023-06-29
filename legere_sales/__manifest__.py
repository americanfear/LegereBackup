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
    
    'depends': ['sale_management'],
    'data': [
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}