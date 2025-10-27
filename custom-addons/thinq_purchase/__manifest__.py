{
    'name': 'Thinq - Purchase',
    'version': '1.0',
    'description': 'This module provides purchase management features for Thinq in Kacamatamoo.',
    'summary': 'This module provides purchase management features for Thinq in Kacamatamoo.',
    'author': 'Thinq Technology',
    'website': 'https://thinq-tech.id',
    'license': 'LGPL-3',
    'category': 'custom',
    'depends': [
        'thinq_base',
        'thinq_inventory',
        'purchase_request',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_request_line_make_purchase_order.xml',
        'views/purchase_request.xml',
        'views/purchase_order.xml',
        'views/purchase_report_supplier_performance_views.xml',
        'views/action_menu.xml',
        'views/menu.xml',
        'views/portal_templates.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_frontend': [
            'thinq_purchase/static/lib/**/*',
            'thinq_purchase/static/src/js/**/*',
        ]
    }
}
