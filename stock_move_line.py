# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    num_boxes = fields.Integer(string='Nº Cajas', default=0)
