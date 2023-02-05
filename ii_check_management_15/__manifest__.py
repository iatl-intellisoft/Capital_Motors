# -*- coding: utf-8 -*-
{
    'name': "Afi Check Management",

    'summary': """
        Check Management""",

    'description': """
        Check Management
    """,
    'author': "Iatl-intellisoft",
    'category': 'Accounting',
    'version': '0.1',
    'depends': ['account'],
    'data': [

        'security/check_security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'wizard/print_check_wizard.xml',
        'views/check_view.xml',
        'views/payment.xml',
        # Check print report
        'report/check_bank_template.xml',
        'report/reports.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
