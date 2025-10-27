# -*- coding: utf-8 -*-
{
    'name': 'Inter Warehouse Transfer',
    'version': '18.0.1.0.0',
    'summary': 'Membuat Internal Warehouse Transfer dengan DO dan GR otomatis',
    'description': """
        Aplikasi ini memungkinkan transfer barang antar gudang dengan alur kerja yang lengkap,
        termasuk pembuatan Delivery Order (DO) dari gudang sumber dan Goods Receipt (GR)
        di gudang tujuan secara otomatis.
    """,
    'category': 'Inventory/Warehouse',
    'author': 'Thinq Technology',
    'website': 'https://www.thinq.id',
    'depends': ['stock', 'mail', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/stock_location_multicompany_rule.xml',
        'data/inter_warehouse_seq.xml',
        'views/res_config_setting.xml',
        'views/inter_warehouse_transfer.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {},
}
