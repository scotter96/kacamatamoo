{
    'name': 'Thinq - Deposit',
    'version': '1.0',
    'description': 'Deposit Feature for Invoice and Vendor Bill - Customization for Thinq module in Kacamatamoo',
    'summary': 'Create Deposit Feature which can be used for Invoice and Vendor Bill',
    'author': 'Thinq Technology',
    'website': 'https://thinq-tech.id',
    'license': 'LGPL-3',
    'category': 'Accounting',
    'depends': [
        'thinq_base',
        'account',  # Untuk invoice/bill
        'base',     # Untuk konversi currency 
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sequence.xml', # generate nomor sequence untuk deposit
        'views/deposit.xml', 
        'views/menu.xml',
        'views/account_move.xml',  # Extend invoice/bill views
        'views/wizard_apply.xml',  # Wizard for applying deposits
        'views/res_company.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
    'application': False,
    'installable': True,
}