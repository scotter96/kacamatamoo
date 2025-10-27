{
    'name': 'Thinq - Base Customization for Kacamatamoo',
    'version': '1.0',
    'description': 'Base customization for Thinq module in Kacamatamoo',
    'summary': 'Base customization for Thinq module in Kacamatamoo',
    'author': 'Thinq Technology',
    'website': 'https://thinq-tech.id',
    'license': 'LGPL-3',
    'category': 'custom',
    'depends': [
        'base',
        'contacts',
        'base_phone',
        'base_user_role',
        'auditlog',
        'query_deluxe',
        'login_user_detail',
        'purchase_request',
        'auth_session_timeout',
        'stock_no_negative',
        'hia_user_login_status',
        'analytic',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/change_role.xml',
        'wizard/multiple_search.xml',
        'wizard/menu_search.xml',
        'views/res_users.xml',
        'views/res_city.xml',
        'views/res_partner.xml',
        'views/menu.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
    'application': False,
    'assets': {
        
    }
}