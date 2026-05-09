# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from collections import defaultdict, namedtuple

from odoo import api, fields, models, tools, _
from odoo.tools import html_escape

from odoo.exceptions import UserError, ValidationError
from odoo.tools import OrderedSet
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

import logging
_logger = logging.getLogger(__name__)


class Product(models.Model):

    _inherit = 'product.product'

    virtual_box = fields.Integer('Cajas', compute='_compute_quantities', compute_sudo=False)

    # Reimplementando
    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.virtual_box', 'stock_move_ids.state', 'stock_move_ids.quantity')
    @api.depends_context(
        'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
        'location', 'warehouse_id', 'allowed_company_ids', 'is_storable'
    )
    def _compute_quantities(self):
        products = self.with_context(prefetch_fields=False).filtered(lambda p: p.type != 'service').with_context(prefetch_fields=True)
        res = products._compute_quantities_dict(self.env.context.get('lot_id'), self.env.context.get('owner_id'), self.env.context.get('package_id'), self.env.context.get('from_date'), self.env.context.get('to_date'))
        # Set qty fields to 0 for all products as services have 0 quantities. Also skips calling __setitem__ on products with 0 quantites in res.
        self.with_context(skip_qty_available_update=True).qty_available = 0.0
        self.incoming_qty = 0.0
        self.outgoing_qty = 0.0
        self.virtual_available = 0.0
        self.free_qty = 0.0
        self.virtual_box = 0.0
        for product in products:
            product.with_context(skip_qty_available_update=True).update({key: val for key, val in res[product.id].items() if val})

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
        dates_in_the_past = False
        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
            domain_move_out += [('restrict_partner_id', '=', owner_id)]
        if 'owners' in self.env.context:
            owners = self.env.context['owners']
            if owners:
                domain_quant += [('owner_id', 'in', self.env.context['owners'])]
            else:
                domain_quant += [('owner_id', '=', False)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if from_date:
            date_date_expected_domain_from = [('date', '>=', from_date)]
            domain_move_in += date_date_expected_domain_from
            domain_move_out += date_date_expected_domain_from
        if to_date:
            date_date_expected_domain_to = [('date', '<=', to_date)]
            domain_move_in += date_date_expected_domain_to
            domain_move_out += date_date_expected_domain_to
        Move = self.env['stock.move'].with_context(active_test=False)
        Quant = self.env['stock.quant'].with_context(active_test=False)
        domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
        domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_in_res = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_in_todo, ['product_id'], ['product_qty:sum'])}
        moves_out_res = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_out_todo, ['product_id'], ['product_qty:sum'])}
        quants_res = {product.id: (quantity, reserved_quantity) for product, quantity, reserved_quantity in Quant._read_group(domain_quant, ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])}
        virtual_box_res = {
            product.id: (virtual_box, reserved_quantity)
            for product, virtual_box, reserved_quantity in Quant._read_group(
                domain_quant,
                ["product_id"],
                ["virtual_box:sum", "reserved_quantity:sum"],
            )
        }
        expired_unreserved_quants_res = {}
        if self.env.context.get('with_expiration'):
            max_date = self.env.context['to_date'] if self.env.context.get('to_date') else self.env.context['with_expiration']
            domain_quant += [('removal_date', '<=', max_date)]
            expired_unreserved_quants_res = {product.id: quantity - reserved_quantity for product, quantity, reserved_quantity in Quant._read_group(domain_quant, ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])}
        moves_in_res_past = defaultdict(float)
        moves_out_res_past = defaultdict(float)
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
            domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done

            groupby = ['product_id', 'product_uom']
            for product, uom, quantity in Move._read_group(domain_move_in_done, groupby, ['quantity:sum']):
                moves_in_res_past[product.id] += uom._compute_quantity(quantity, product.uom_id)

            for product, uom, quantity in Move._read_group(domain_move_out_done, groupby, ['quantity:sum']):
                moves_out_res_past[product.id] += uom._compute_quantity(quantity, product.uom_id)

        res = dict()
        for product in self.with_context(prefetch_fields=False):
            origin_product_id = product._origin.id
            product_id = product.id
            if not origin_product_id or (
                origin_product_id not in quants_res
                and origin_product_id not in moves_in_res
                and origin_product_id not in moves_out_res
                and origin_product_id not in moves_in_res_past
                and origin_product_id not in moves_out_res_past
                and origin_product_id not in expired_unreserved_quants_res
            ):
                res[product_id] = dict.fromkeys(
                    ['qty_available', 'free_qty', 'incoming_qty', 'outgoing_qty', 'virtual_available', 'virtual_box'],
                    0.0,
                )
                continue
            res[product_id] = {}
            if dates_in_the_past:
                qty_available = quants_res.get(origin_product_id, [0.0])[0] - moves_in_res_past.get(origin_product_id, 0.0) + moves_out_res_past.get(origin_product_id, 0.0)
                virtual_available = 0
            else:
                qty_available = quants_res.get(origin_product_id, [0.0])[0]
                virtual_available = virtual_box_res.get(origin_product_id, [0.0])[0]

            res[product_id]['virtual_box'] = product.uom_id.round(virtual_available)

            reserved_quantity = quants_res.get(origin_product_id, [False, 0.0])[1]
            expired_unreserved_qty = expired_unreserved_quants_res.get(origin_product_id, 0.0)
            res[product_id]['qty_available'] = product.uom_id.round(qty_available)
            res[product_id]['free_qty'] = product.uom_id.round(qty_available - reserved_quantity - expired_unreserved_qty)
            res[product_id]['incoming_qty'] = product.uom_id.round(moves_in_res.get(origin_product_id, 0.0))
            res[product_id]['outgoing_qty'] = product.uom_id.round(moves_out_res.get(origin_product_id, 0.0))
            res[product_id]['virtual_available'] = product.uom_id.round(
                qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'] - expired_unreserved_qty,
            )

        return res

    # Odoo17 Old code, to check if we can reuse some of it
    # @api.depends('stock_move_ids.product_qty', 'stock_move_ids.virtual_box', 'stock_move_ids.state')
    # @api.depends_context(
    #     'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
    #     'location', 'warehouse',
    # )
    # def _compute_quantities(self):
    #     products = self.filtered(lambda p: p.type != 'service')
    #     res = products._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'),
    #                                             self._context.get('package_id'), self._context.get('from_date'),
    #                                             self._context.get('to_date'))
    #     for product in products:
    #         product.update(res[product.id])
    #     # Services need to be set with 0.0 for all quantities
    #     services = self - products
    #     services.qty_available = 0.0
    #     services.incoming_qty = 0.0
    #     services.outgoing_qty = 0.0
    #     services.virtual_available = 0.0
    #     services.free_qty = 0.0
    #     services.virtual_box = 0.0

    # # Reimplementando
    # def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
    #     domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
    #     domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
    #     dates_in_the_past = False
    #     # only to_date as to_date will correspond to qty_available
    #     to_date = fields.Datetime.to_datetime(to_date)
    #     if to_date and to_date < fields.Datetime.now():
    #         dates_in_the_past = True

    #     domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
    #     domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
    #     if lot_id is not None:
    #         domain_quant += [('lot_id', '=', lot_id)]
    #     if owner_id is not None:
    #         domain_quant += [('owner_id', '=', owner_id)]
    #         domain_move_in += [('restrict_partner_id', '=', owner_id)]
    #         domain_move_out += [('restrict_partner_id', '=', owner_id)]
    #     if package_id is not None:
    #         domain_quant += [('package_id', '=', package_id)]
    #     if dates_in_the_past:
    #         domain_move_in_done = list(domain_move_in)
    #         domain_move_out_done = list(domain_move_out)
    #     if from_date:
    #         date_date_expected_domain_from = [('date', '>=', from_date)]
    #         domain_move_in += date_date_expected_domain_from
    #         domain_move_out += date_date_expected_domain_from
    #     if to_date:
    #         date_date_expected_domain_to = [('date', '<=', to_date)]
    #         domain_move_in += date_date_expected_domain_to
    #         domain_move_out += date_date_expected_domain_to

    #     Move = self.env['stock.move'].with_context(active_test=False)
    #     Quant = self.env['stock.quant'].with_context(active_test=False)
    #     domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
    #     domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
    #     moves_in_res = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_in_todo, ['product_id'], ['product_qty:sum'])}
    #     moves_out_res = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_out_todo, ['product_id'], ['product_qty:sum'])}
    #     quants_res = {product.id: (quantity, reserved_quantity) for product, quantity, reserved_quantity in Quant._read_group(domain_quant, ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])}

    #     virtual_box_res = {product.id: (virtual_box, reserved_quantity) for product, virtual_box, reserved_quantity in
    #                   Quant._read_group(domain_quant, ['product_id'], ['virtual_box:sum', 'reserved_quantity:sum'])}

    #     if dates_in_the_past:
    #         # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
    #         domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
    #         domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
    #         moves_in_res_past = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_in_done, ['product_id'], ['product_qty:sum'])}
    #         moves_out_res_past = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_out_done, ['product_id'], ['product_qty:sum'])}

    #     res = dict()
    #     for product in self.with_context(prefetch_fields=False):
    #         origin_product_id = product._origin.id
    #         product_id = product.id
    #         if not origin_product_id:
    #             res[product_id] = dict.fromkeys(
    #                 ['qty_available', 'free_qty', 'incoming_qty', 'outgoing_qty', 'virtual_available', 'virtual_box'],
    #                 0.0,
    #             )
    #             continue
    #         rounding = product.uom_id.rounding
    #         res[product_id] = {}
    #         if dates_in_the_past:
    #             qty_available = quants_res.get(origin_product_id, [0.0])[0] - moves_in_res_past.get(origin_product_id, 0.0) + moves_out_res_past.get(origin_product_id, 0.0)
    #             virtual_available = 0
    #         else:
    #             qty_available = quants_res.get(origin_product_id, [0.0])[0]
    #             virtual_available = virtual_box_res.get(origin_product_id, [0.0])[0]

    #         reserved_quantity = quants_res.get(origin_product_id, [False, 0.0])[1]

    #         res[product_id]['virtual_box'] = float_round(virtual_available, precision_rounding=rounding)

    #         res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
    #         res[product_id]['free_qty'] = float_round(qty_available - reserved_quantity, precision_rounding=rounding)
    #         res[product_id]['incoming_qty'] = float_round(moves_in_res.get(origin_product_id, 0.0), precision_rounding=rounding)
    #         res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(origin_product_id, 0.0), precision_rounding=rounding)
    #         res[product_id]['virtual_available'] = float_round(
    #             qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'],
    #             precision_rounding=rounding)

    #     return res
