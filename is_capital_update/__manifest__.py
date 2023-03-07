# -*- coding: utf-8 -*-
{
    'name': "Capital HR Custmization",
    'summary': """
       Loans,Payroll,Overtime,Leave Customization""",
    'description': """ This Module contains customization of loan in including all types,payroll , Leave and overtime 
                        management.                
    """,
    'author': "IntelliSoft Software",
    'website': "http://www.intellisoft.sd",
    'category': 'Human Resources',
    'version': '16.0.0.1',
    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_attendance', 'hr_contract', 'hr_payroll', 'hr_holidays',
                'hr_payroll_account', 'account', 'ii_simple_check_management', 'is_hr_capital'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/update.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}
