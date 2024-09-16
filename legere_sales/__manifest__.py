{
    'name': 'Legere Sales',
    'version': '1.0.9',
    'category': 'Sales/Sales',
    'summary': """customization related to sales module""",
    'description': """
        customization related to sales module
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['sale_management', 'sale_project', 'sale_stock', 'sale_mrp', 'purchase_stock', 'stock_dropshipping', 'base_automation', 'legere_legacy', 'legere_sales_commission'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/project_task_views.xml',
        'views/res_config_setting_views.xml',
        'views/stock_picking_views.xml',
        'wizard/check_and_confirm_views.xml',
        'report/customer_sale_report_views.xml',
        'report/report_saleorder_document.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}