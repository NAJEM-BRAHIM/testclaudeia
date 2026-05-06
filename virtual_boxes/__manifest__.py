# -*- coding: utf-8 -*-
{
    'name': 'Cajas Virtuales',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Control de número de cajas en ventas, stock y facturas',
    'depends': ['sale_stock', 'account'],
    'data': [
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/account_move_views.xml',
        'report/report_invoice.xml',
        'report/report_sale.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
