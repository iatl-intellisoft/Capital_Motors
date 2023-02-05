# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Capital Stock Customization',
    'version': '16.0.1.1',
    'author': 'Intellisoft Software',
    'summary': 'Stock Module',
    'description': """
This module allows you to manage your Sale.
===========================================================

Easily manage receipts and delivery orders , Control Products and all operations are stock moves between locations.""",

    'website': 'http://www.intellisoft.sd',
    'images': ['static/description/icon.png'],
    'depends': ['ii_stock_valuation_currency', 'stock', 'sale'],
    'sequence': 13,
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/stock_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
