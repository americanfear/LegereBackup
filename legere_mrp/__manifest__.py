{
    'name': 'Legere MRP',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': """customization related to mrp module""",
    'description': """
        customization related to mrp module
    """,
    'license': 'Other proprietary',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    
    'depends': ['mrp', 'legere_legacy'],
    'data': [
        'views/mrp_production_views.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,

}