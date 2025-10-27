{
    'name': 'Thinq - Project',
    'version': '1.0',
    'description': 'Customization for Thinq module in Kacamatamoo (Project)',
    'summary': 'Customization for Thinq module in Kacamatamoo (Project)',
    'author': 'Thinq Technology',
    'website': 'https://thinq-tech.id',
    'license': 'LGPL-3',
    'category': 'custom',
    'depends': [
        'thinq_base',
        'project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_action.xml',
        'views/project.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
    'application': False,
}