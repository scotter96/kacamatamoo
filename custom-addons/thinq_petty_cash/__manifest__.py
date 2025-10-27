{
    'name': 'Thinq - Petty Cash',
    'version': '1.0',
    'description': 'This module provides petty cash management features for Thinq in Kacamatamoo.',
    'summary': 'This module provides petty cash management features for Thinq in Kacamatamoo.',
    'author': 'Thinq Technology',
    'website': 'https://thinq-tech.id',
    'license': 'LGPL-3',
    'category': 'custom',
    'depends': [
        'thinq_base',
        'accountant',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/petty_cash.xml',
        'views/product.xml',
        'views/menu.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
    'application': False,
    'assets': {
        
    }
}