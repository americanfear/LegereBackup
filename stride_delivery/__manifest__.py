{
    'name': "Stride: Delivery",
    'summary': """
        Stride Delivery""",
    'description': """
       Stride Delivery
    """,
    'author': "Dream Mountain Services",
    'website': "http://dreammtn.services",
    'support': 'support@DreamMtn.Services',   

    'version': '1.0',
    'license': 'Other proprietary',
    'depends': ['sale_stock', 'delivery', 'web_ir_actions_act_multi', 'sms'],
    'external_dependencies': {
        'python': ['easypost'],
    },
    'images': [],
    'data': [
        'security/ir.model.access.csv',
        'data/easypost_carrier_data.xml',
        'data/mail_template_data_easypost.xml',
        'data/sms_template_data_easypost.xml',
        'data/sequence.xml',
        'views/views.xml',
        'views/product_package_view.xml',
        'views/stock_picking.xml',
        'wizard/choose_delivery_carrier_views.xml',
        'wizard/choose_delivery_package_views.xml',
        'wizard/shipping_rate_views.xml',
        'views/res_config_setting_views.xml',
        'views/shipment_tracking_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'stride_delivery/static/src/scss/shipment_tracking.scss',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installble': True,
    'auto_install': False,   
}