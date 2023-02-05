#######################################################################
#    IntelliSoft Software                                             #
#    Copyright (C) 2019 (<http://intellisoft.sd>) all rights reserved.#
#######################################################################

{
    'name': 'IntelliSoft Accounting Approval 14',
    'author': 'IntelliSoft Software',
    'website': 'http://www.intellisoft.sd',
    'description': "A module that customizes the accounting module. Migrated to Odoo 13.",
    'depends': ['account', 'hr'],
    'category': 'Accounting',
    'data': [
        'security/security_view.xml',
        'security/ir.model.access.csv',
        'data/load.xml',
        'data/approval_sequence.xml',
        'reports/reports_registration.xml',
        'reports/report_finance_approval.xml',
        'views/res_users_view.xml',
        'views/res_currency_view.xml',
        'views/finance_approval_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3'
}
