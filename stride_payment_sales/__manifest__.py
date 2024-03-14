{
    'name': 'Stride: Payment Sales',
    'version': '16.0.1.0.2'
    'category': 'Sales/Payment',
    'summary': """Stride Payment""",
    'description': """Stride Payment""",
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stride_sale_payment_views.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stride_payment_sales/static/src/js/form_view.js',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,

}
