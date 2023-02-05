{
    'name': 'Capital Inventory Management',
    'version': '16.0.1.0',
    'author': 'Intellisoft',
    'category': 'Inventory',
    'description': """
     Capital Inventory custominzations
    """,
    'depends': ['sale_management', 'stock', 'stock_account', 'stock_landed_costs', 'dev_landed_cost_average_price', 'purchase'],
    'data': [
        'security/inventory.xml',
        'security/ir.model.access.csv',
        'wizard/stock_search_views.xml',
        'report/report_picking_ticket.xml',
        'views/inventory_view.xml',
        'views/inventory_reports.xml',
        'views/inventory_view_custom.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
