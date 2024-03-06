{
    'name': 'Legere Legacy',
    'version': '1.0.1',
    'category': 'Tools',
    'summary': """Store Legacy Data""",
    'description': """
        Store Legacy Data
        ====================
        Invoices
        Orders
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/legere_legacy_order_views.xml',
        'views/legere_legacy_invoice_views.xml',
        'views/res_partner_views.xml',
        'report/report_legere_invoice.xml',
        'report/report_legere_order.xml',
        'report/report.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}