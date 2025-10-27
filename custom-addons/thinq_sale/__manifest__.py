{
    'name': 'Thinq - Sales',
    'version': '1.0',
    'description': 'Customization for Thinq module in Kacamatamoo (Sale)',
    'summary': 'Customization for Thinq module in Kacamatamoo (Sale)',
    'author': 'Thinq Technology',
    'website': 'https://thinq-tech.id',
    'license': 'LGPL-3',
    'category': 'custom',
    'depends': [
        'thinq_base',
        'sale_management',
        'stock',
        'loyalty',
    ],
    'data': [
        'views/res_config_settings.xml',
        'security/group.xml',
        'views/sale.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
    'application': False,
}