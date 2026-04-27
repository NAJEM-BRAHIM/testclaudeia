{
    'name': 'Partner NIF',
    'version': '19.0.1.0.0',
    'summary': 'Añade el campo NIF al contacto (res.partner)',
    'category': 'Contacts',
    'author': 'Custom',
    'depends': ['contacts'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
