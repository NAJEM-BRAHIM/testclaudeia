# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    virtual_box = fields.Integer('Boxes')


class AccountMove(models.Model):

    _inherit = 'account.move'

    total_virtual_box = fields.Integer(
        string='Total Cajas',
        compute='_compute_totals_virtualbox',
        store=True,
    )
    total_quantity = fields.Float(
        string='Total Unidades',
        compute='_compute_totals_virtualbox',
        store=True,
        digits='Product Unit of Measure',
    )

    @api.depends('invoice_line_ids.virtual_box', 'invoice_line_ids.quantity')
    def _compute_totals_virtualbox(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
            move.total_virtual_box = sum(lines.mapped('virtual_box'))
            move.total_quantity = sum(lines.mapped('quantity'))
