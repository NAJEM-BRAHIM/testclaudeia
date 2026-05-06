# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    num_boxes = fields.Integer(string='Nº Cajas')

    def _prepare_invoice_line(self, **optional_values):
        result = super()._prepare_invoice_line(**optional_values)
        result['num_boxes'] = self.num_boxes
        return result

    def _prepare_procurement_values(self):
        values = super()._prepare_procurement_values()
        values['num_boxes'] = self.num_boxes
        return values
