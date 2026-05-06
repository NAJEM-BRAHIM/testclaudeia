# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    num_boxes = fields.Integer(
        string='Nº Cajas',
        compute='_compute_num_boxes',
        store=True,
        readonly=False,
    )

    @api.depends('sale_line_id.num_boxes')
    def _compute_num_boxes(self):
        for move in self:
            if move.sale_line_id:
                move.num_boxes = move.sale_line_id.num_boxes

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        res = super()._prepare_move_line_vals(quantity, reserved_quant)
        res['num_boxes'] = self.num_boxes
        return res

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        self._update_quant_num_boxes()
        return res

    def _update_quant_num_boxes(self):
        """Actualiza num_boxes en stock.quant al validar el movimiento."""
        StockQuant = self.env['stock.quant'].sudo()
        for move in self.filtered(lambda m: m.state == 'done'):
            for ml in move.move_line_ids.filtered(lambda l: l.num_boxes):
                # Sumar cajas en ubicación destino (interna)
                if ml.location_dest_id.usage == 'internal':
                    quant = StockQuant.search([
                        ('product_id', '=', ml.product_id.id),
                        ('location_id', '=', ml.location_dest_id.id),
                        ('lot_id', '=', ml.lot_id.id if ml.lot_id else False),
                    ], limit=1)
                    if quant:
                        quant.num_boxes += ml.num_boxes
                # Restar cajas de ubicación origen (interna)
                if ml.location_id.usage == 'internal':
                    quant = StockQuant.search([
                        ('product_id', '=', ml.product_id.id),
                        ('location_id', '=', ml.location_id.id),
                        ('lot_id', '=', ml.lot_id.id if ml.lot_id else False),
                    ], limit=1)
                    if quant:
                        quant.num_boxes = max(0, quant.num_boxes - ml.num_boxes)
