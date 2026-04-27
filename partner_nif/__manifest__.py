{
    'name': 'Partner NIF',
    'version': '19.0.1.0.0',
    'summary': 'Añade el campo NIF al contacto (res.partner)',
    'category': 'Contacts',
    'author': 'Custom',
    'depends': ['contacts', 'account', 'sale'],
    'data': [
        'views/res_partner_views.xml',
        'report/report_invoice_nif.xml',
        'report/report_sale_nif.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
