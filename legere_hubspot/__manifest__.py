{
    'name': 'Legere Hubspot',
    'version': '1.2',
    'category': 'Tools',
    'summary': """Integration With Hubspot""",
    'description': """
        Integration With Hubspot
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/service_cron.xml',
        'views/hubspot_connector_views.xml',
        'views/res_partner_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}