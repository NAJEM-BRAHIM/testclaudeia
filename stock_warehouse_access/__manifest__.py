{
    'name': 'Stock Warehouse Access',
    'version': '19.0.1.0.0',
    'summary': 'Restringe el acceso de usuarios a almacenes específicos',
    'category': 'Inventory/Inventory',
    'author': 'Custom',
    'depends': ['stock'],
    'data': [
        'security/stock_warehouse_access_rules.xml',
        'views/stock_warehouse_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
