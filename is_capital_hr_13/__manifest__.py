#######################################################################
#    IntelliSoft Software                                             #
#    Copyright (C) 2019 (<http://intellisoft.sd>) all rights reserved.#
#######################################################################

{
    'name': 'IntelliSoft HR 13',
    'author': 'IntelliSoft Software',
    'website': 'http://www.intellisoft.sd',
    'description': "A module that customizes the accounting module. Migrated to Odoo 12.",
    'depends': ['account', 'hr', 'ii_check_management_15', 'hr_recruitment', 'hr_attendance',
                'hr_contract', 'survey', 'is_accounting_approval_15'],
                # to-do: Add 'is_cap_contract' in depends to print contract report
    'category': 'Accounting',
    'data': [
        'data/capital_application_form.xml',
        'data/hr_capital_cron.xml',
        'security/ir.model.access.csv',
        'views/is_hr_view.xml',
        'report/report_registration.xml',
        'report/report_contract.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
