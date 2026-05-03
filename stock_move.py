# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.tools import float_compare

import logging
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    virtual_box = fields.Integer('Boxes')

    def _prepare_invoice_line(self, **optional_values):    
        result = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        result.update({
            'virtual_box': self.virtual_box
            })        
        return result

    def _prepare_procurement_values(self):
        values = super(SaleOrderLine, self)._prepare_procurement_values()
        values.update({'virtual_box': self.virtual_box})
        return values
