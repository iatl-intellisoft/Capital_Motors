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
                'hr_payroll_account', 'account', 'is_accounting_approval_14'],

    # always loaded
    'data': [
        'security/is_hr_cap_security.xml',
        'security/ir.model.access.csv',
        'data/is_cap_sequence.xml',
        'data/is_cap_payroll_structure.xml',
        'data/employee_code_data.xml',
        'report/report_registration.xml',
        'report/report_contract.xml',
        # 'data/capital_application_form.xml',
        'data/hr_capital_cron.xml',
        'views/is_cap_employee_view.xml',
        'views/is_cap_config_view.xml',
        'views/is_cap_contract_view.xml',
        'views/is_cap_loan_view.xml',
        'views/is_cap_long_loan_view.xml',
        'views/is_cap_overtime_view.xml',
        'views/is_cap_penalty_view.xml',
        'views/is_cap_trip.xml',
        'views/is_cap_payslip_view.xml',
        'views/is_recruitment_view.xml',
        'views/is_cap_leave_views.xml',
        'views/is_cap_leaves_menuitem.xml',
        # 'views/is_cap_salary_transfer_view.xml',
        'wizard/wizard_overtime_view.xml',
        'wizard/insurance_basic_list_report.xml',
        'wizard/pay_sheet_view.xml',
        'wizard/other_bank_view.xml',
        'wizard/penalty.xml',
        # 'wizard/hr_transfer_salary_by_employees_views.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}
