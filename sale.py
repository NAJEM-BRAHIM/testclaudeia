# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    num_boxes = fields.Integer(
        string='Nº Cajas',
        compute='_compute_num_boxes',
        store=True,
        readonly=False,
    )

    @api.depends('sale_line_ids.num_boxes')
    def _compute_num_boxes(self):
        for line in self:
            line.num_boxes = sum(line.sale_line_ids.mapped('num_boxes'))


class AccountMove(models.Model):
    _inherit = 'account.move'

    total_boxes = fields.Integer(
        string='Total Cajas',
        compute='_compute_totals_boxes',
        store=False,
    )
    total_quantity = fields.Float(
        string='Total Unidades',
        compute='_compute_totals_boxes',
        store=False,
        digits='Product Unit of Measure',
    )

    @api.depends('invoice_line_ids.num_boxes', 'invoice_line_ids.quantity',
                 'invoice_line_ids.display_type')
    def _compute_totals_boxes(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            move.total_boxes = sum(lines.mapped('num_boxes'))
            move.total_quantity = sum(lines.mapped('quantity'))
