{
    'name': 'Stride: payment sales authorize',
    'version': '1.0',
    'category': 'Sales/Payment',
    'summary': """payment sales authorize""",
    'description': """payment sales authorize""",
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['stride_payment_sales', 'payment_authorize'],
    'data': [
        'wizard/stride_sale_payment_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'stride_payment_sales_authorize/static/src/js/form_view.js',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}