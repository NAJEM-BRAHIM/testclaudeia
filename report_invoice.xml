# -*- coding: utf-8 -*-
from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    num_boxes = fields.Integer(
        string='Nº Cajas',
        default=0,
        help='Número de cajas en stock. Se actualiza automáticamente al validar albaranes.',
    )
