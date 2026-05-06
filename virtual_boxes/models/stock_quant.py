# -*- coding: utf-8 -*-
from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    num_boxes = fields.Integer(string='Nº Cajas')

    def _get_inventory_fields_write(self):
        res = super()._get_inventory_fields_write()
        res += ['num_boxes']
        return res
