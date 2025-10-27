{
    'name': 'Thinq - Asset',
    'version': '1.0',
    'description': 'Customization for Thinq module in Kacamatamoo (Asset)',
    'summary': 'Customization for Thinq module in Kacamatamoo (Asset)',
    'author': 'Thinq Technology',
    'website': 'https://thinq-tech.id',
    'license': 'LGPL-3',
    'category': 'custom',
    'depends': [
        'account_asset',
        'thinq_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/server_actions.xml',
        
        'wizard/asset_label_layout.xml',
        
        'views/account_asset_views.xml',
        'views/ga_asset_attribute_views.xml',
        'views/ga_asset_categ_views.xml',
        'views/menu_assets.xml',

        'reports/asset_label_report.xml',
        'reports/action.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
    'application': False,
}