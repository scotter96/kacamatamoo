{
    'name': 'Thinq - Point of Sale',
    'version': '1.0',
    'description': 'Customization for Thinq module in Kacamatamoo (POS)',
    'summary': 'Customization for Thinq module in Kacamatamoo (POS)',
    'author': 'Thinq Technology',
    'website': 'https://thinq-tech.id',
    'license': 'LGPL-3',
    'category': 'custom',
    'depends': [
        'l10n_id_efaktur',
        'thinq_inventory',
        'point_of_sale',
        'pos_hr',
        'product_bundle_all',
        'thinq_url_shortener',
        'loyalty',
    ],
    'data': [
        'security/ir.model.access.csv',

        'reports/invoice_report_template.xml',
        'reports/invoice_report.xml',

        'views/pos_promotion.xml',
        'views/pos_order_refraction_views.xml',
        'views/pos_order_views.xml',
        'views/loyalty_generate_code.xml',
        'views/loyalty_program.xml',
        'views/loyalty_reward.xml',
        'views/res_partner_views.xml',
        'views/return_views.xml',
        'views/pos_config_views.xml',
    ],
    'demo': [
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "thinq_pos/static/src/**/*",
        ],
        'web.assets_backend': [
            'thinq_pos/static/src/css/pos_config_small_input.css',
        ],
    },
    'auto_install': False,
    'application': False,
}
