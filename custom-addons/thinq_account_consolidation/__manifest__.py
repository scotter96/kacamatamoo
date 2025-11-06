{
    "name": "Thinq Account Consolidation",
    "version": "18.0.1.0.0",
    "author": "Thinq Tech",
    "license": "AGPL-3",
    "category": "Generic Modules/Accounting",
    "website": "thinq-tech.id",
    "depends": [
        'accountant',
        'account',
        'thinq_base',
    ],
    "data": [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/consol_coa.xml',
        'views/consol_company.xml',
        'views/consol_elimination.xml',
        'views/consol_link_view.xml',
        'views/consol_cashflow_map.xml',
        'views/consol_rule.xml',
        'wizard/consolidation_base.xml',
        'wizard/consolidation_result.xml',
        'wizard/consol_group.xml',
        # 'views/res_config_settings.xml',
        
        'views/consolidation_menu.xml'
    ],
    "installable": True,
}
