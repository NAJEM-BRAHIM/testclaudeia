from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    nif = fields.Char(string='NIF', help='Número de Identificación Fiscal')
