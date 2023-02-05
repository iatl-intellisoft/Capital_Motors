#######################################################################
#    IntelliSoft Software                                             #
#    Copyright (C) 2019 (<http://intellisoft.sd>) all rights reserved.#
#######################################################################

{
    'name': 'is_capital_accounting_13',
    'author': 'IntelliSoft Software',
    'website': 'http://www.intellisoft.sd',
    'description': "A module that customizes the accounting module.",
    'depends': ['account', 'stock_account', 'product', 'is_hr_capital'],
    'category': 'Accounting',
    'data': [
        'security/ir.model.access.csv',
        # 'views/custom_valuation_tree.xml',
        'wizard/partner_account_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
