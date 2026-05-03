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


class StockMoveLine(models.Model):

    _inherit = 'stock.move.line'

    virtual_box = fields.Integer(
        'Cajas',
        compute='_compute_virtual_box_line',
        store=True,
        readonly=False,
    )

    @api.depends('move_id.virtual_box', 'move_id.move_line_ids')
    def _compute_virtual_box_line(self):
        for line in self:
            move = line.move_id
            if not move:
                line.virtual_box = 0
                continue
            # La primera línea del movimiento recibe todas las cajas, el resto 0
            first_line = move.move_line_ids.sorted('id')[:1]
            if line == first_line:
                line.virtual_box = move.virtual_box
            else:
                line.virtual_box = 0

    # Reimplementando

    def _get_aggregated_product_quantities(self, **kwargs):

        # Call original method
        result = super()._get_aggregated_product_quantities(**kwargs)

        # Add virtual_box in result
        for line in self:

            if not line.virtual_box:
                continue

            props = self._get_aggregated_properties(move_line=line)
            line_key = props["line_key"]

            if line_key in result:

                # Initialize if missing
                if "virtual_box" not in result[line_key]:
                    result[line_key]["virtual_box"] = 0

                # Sumar cajas de la línea (ya distribuidas proporcionalmente por lote)
                result[line_key]["virtual_box"] += line.virtual_box

        return result

    # def _get_aggregated_product_quantities(self, **kwargs):
    #     """ Returns a dictionary of products (key = id+name+description+uom+packaging) and corresponding values of interest.

    #     Allows aggregation of data across separate move lines for the same product. This is expected to be useful
    #     in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
    #     the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
    #     expected to already be properly grouped by line.

    #     returns: dictionary {product_id+name+description+uom+packaging: {product, name, description, quantity, product_uom, packaging}, ...}
    #     """
    #     aggregated_move_lines = {}

    #     def get_aggregated_properties(move_line=False, move=False):
    #         move = move or move_line.move_id
    #         uom = move.product_uom or move_line.product_uom_id
    #         name = move.product_id.display_name
    #         description = move.description_picking
    #         if description == name or description == move.product_id.name:
    #             description = False
    #         product = move.product_id
    #         line_key = f'{product.id}_{product.display_name}_{description or ""}_{uom.id}_{move.product_packaging_id or ""}'
    #         return (line_key, name, description, uom, move.product_packaging_id)

    #     def _compute_packaging_qtys(aggregated_move_lines):
    #         # Needs to be computed after aggregation of line qtys
    #         for line in aggregated_move_lines.values():
    #             if line['packaging']:
    #                 line['packaging_qty'] = line['packaging']._compute_qty(line['qty_ordered'], line['product_uom'])
    #                 line['packaging_quantity'] = line['packaging']._compute_qty(line['quantity'], line['product_uom'])
    #         return aggregated_move_lines

    #     # Loops to get backorders, backorders' backorders, and so and so...
    #     backorders = self.env['stock.picking']
    #     pickings = self.picking_id
    #     while pickings.backorder_ids:
    #         backorders |= pickings.backorder_ids
    #         pickings = pickings.backorder_ids

    #     for move_line in self:
    #         if kwargs.get('except_package') and move_line.result_package_id:
    #             continue
    #         line_key, name, description, uom, packaging = get_aggregated_properties(move_line=move_line)
    #         quantity = move_line.product_uom_id._compute_quantity(move_line.quantity, uom)
    #         if line_key not in aggregated_move_lines:
    #             qty_ordered = None
    #             if backorders and not kwargs.get('strict'):
    #                 qty_ordered = move_line.move_id.product_uom_qty
    #                 # Filters on the aggregation key (product, description and uom) to add the
    #                 # quantities delayed to backorders to retrieve the original ordered qty.
    #                 following_move_lines = backorders.move_line_ids.filtered(
    #                     lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key
    #                 )
    #                 qty_ordered += sum(following_move_lines.move_id.mapped('product_uom_qty'))
    #                 # Remove the done quantities of the other move lines of the stock move
    #                 previous_move_lines = move_line.move_id.move_line_ids.filtered(
    #                     lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key and ml.id != move_line.id
    #                 )
    #                 qty_ordered -= sum(
    #                     [m.product_uom_id._compute_quantity(m.quantity, uom) for m in previous_move_lines])
    #             aggregated_move_lines[line_key] = {
    #                 'name': name,
    #                 'description': description,
    #                 'quantity': quantity,
    #                 'qty_ordered': qty_ordered or quantity,
    #                 'product_uom': uom,
    #                 'product': move_line.product_id,
    #                 'packaging': packaging,
    #                 'virtual_box': move_line.move_id.virtual_box,
    #             }
    #         else:
    #             aggregated_move_lines[line_key]['qty_ordered'] += quantity
    #             aggregated_move_lines[line_key]['quantity'] += quantity
    #             aggregated_move_lines[line_key]['virtual_box'] += move_line.move_id.virtual_box

    #     # Does the same for empty move line to retrieve the ordered qty. for partially done moves
    #     # (as they are splitted when the transfer is done and empty moves don't have move lines).
    #     if kwargs.get('strict'):
    #         return _compute_packaging_qtys(aggregated_move_lines)
    #     pickings = (self.picking_id | backorders)
    #     for empty_move in pickings.move_ids:
    #         if not (empty_move.state == "cancel" and empty_move.product_uom_qty
    #                 and float_is_zero(empty_move.quantity, precision_rounding=empty_move.product_uom.rounding)):
    #             continue
    #         line_key, name, description, uom, packaging = get_aggregated_properties(move=empty_move)

    #         if line_key not in aggregated_move_lines:
    #             qty_ordered = empty_move.product_uom_qty
    #             aggregated_move_lines[line_key] = {
    #                 'name': name,
    #                 'description': description,
    #                 'quantity': False,
    #                 'qty_ordered': qty_ordered,
    #                 'product_uom': uom,
    #                 'product': empty_move.product_id,
    #                 'packaging': packaging,
    #             }
    #         else:
    #             aggregated_move_lines[line_key]['qty_ordered'] += empty_move.product_uom_qty

    #     return _compute_packaging_qtys(aggregated_move_lines)

    # Reimplementando
    def _synchronize_quant(self, quantity, location, action="available", in_date=False, **quants_value):
        """ quantity should be express in product's UoM"""
        lot = quants_value.get('lot', self.lot_id)
        package = quants_value.get('package', self.package_id)
        owner = quants_value.get('owner', self.owner_id)
        available_qty = 0
        virtual_box = quants_value.get("virtual_box")

        if not self.product_id.is_storable or self.product_uom_id.is_zero(quantity):
            return 0, False
        if action == "available":
            available_qty, in_date = self.env['stock.quant']._update_available_quantity(self.product_id, location, quantity, lot_id=lot, package_id=package, owner_id=owner, in_date=in_date, virtual_box=virtual_box)
        elif action == "reserved" and not self.move_id._should_bypass_reservation(location):
            self.env['stock.quant']._update_reserved_quantity(self.product_id, location, quantity, lot_id=lot, package_id=package, owner_id=owner)
        if available_qty < 0 and lot:
            # see if we can compensate the negative quants with some untracked quants
            untracked_qty = self.env['stock.quant']._get_available_quantity(self.product_id, location, lot_id=False, package_id=package, owner_id=owner, strict=True)
            if not untracked_qty:
                return available_qty, in_date
            taken_from_untracked_qty = min(untracked_qty, abs(quantity))
            self.env['stock.quant']._update_available_quantity(self.product_id, location, -taken_from_untracked_qty, lot_id=False, package_id=package, owner_id=owner, in_date=in_date, virtual_box=-virtual_box)
            self.env['stock.quant']._update_available_quantity(self.product_id, location, taken_from_untracked_qty, lot_id=lot, package_id=package, owner_id=owner, in_date=in_date, virtual_box=virtual_box)
        return available_qty, in_date

    # def _synchronize_quant(self, quantity, location, action="available", in_date=False, **quants_value):
    #     """ quantity should be express in product's UoM"""
    #     lot = quants_value.get('lot', self.lot_id)
    #     package = quants_value.get('package', self.package_id)
    #     owner = quants_value.get('owner', self.owner_id)
    #     available_qty = 0

    #     virtual_box = quants_value.get("virtual_box")

    #     if self.product_id.type != 'product' or float_is_zero(quantity, precision_rounding=self.product_uom_id.rounding):
    #         return 0, False
    #     if action == "available":
    #         available_qty, in_date = self.env['stock.quant']._update_available_quantity(self.product_id, location, quantity, lot_id=lot, package_id=package, owner_id=owner, in_date=in_date, virtual_box=virtual_box)
    #     elif action == "reserved" and not self.move_id._should_bypass_reservation():
    #         self.env['stock.quant']._update_reserved_quantity(self.product_id, location, quantity, lot_id=lot, package_id=package, owner_id=owner)
    #     if available_qty < 0 and lot:
    #         # see if we can compensate the negative quants with some untracked quants
    #         untracked_qty = self.env['stock.quant']._get_available_quantity(self.product_id, location, lot_id=False, package_id=package, owner_id=owner, strict=True)
    #         if not untracked_qty:
    #             return available_qty, in_date
    #         taken_from_untracked_qty = min(untracked_qty, abs(quantity))
    #         self.env['stock.quant']._update_available_quantity(self.product_id, location, -taken_from_untracked_qty, lot_id=False, package_id=package, owner_id=owner, in_date=in_date, virtual_box=-virtual_box)
    #         self.env['stock.quant']._update_available_quantity(self.product_id, location, taken_from_untracked_qty, lot_id=lot, package_id=package, owner_id=owner, in_date=in_date, virtual_box=virtual_box)
    #     return available_qty, in_date

    # Reimplementando
    def _action_done(self):
        """ This method is called during a move's `action_done`. It'll actually move a quant from
        the source location to the destination location, and unreserve if needed in the source
        location.

        This method is intended to be called on all the move lines of a move. This method is not
        intended to be called when editing a `done` move (that's what the override of `write` here
        is done.
        """

        # First, we loop over all the move lines to do a preliminary check: `quantity` should not
        # be negative and, according to the presence of a picking type or a linked inventory
        # adjustment, enforce some rules on the `lot_id` field. If `quantity` is null, we unlink
        # the line. It is mandatory in order to free the reservation and correctly apply
        # `action_done` on the next move lines.
        ml_ids_tracked_without_lot = OrderedSet()
        ml_ids_to_delete = OrderedSet()
        ml_ids_to_create_lot = OrderedSet()
        ml_ids_to_check = defaultdict(OrderedSet)

        for ml in self:
            # Check here if `ml.quantity` respects the rounding of `ml.product_uom_id`.
            uom_qty = ml.product_uom_id.round(ml.quantity, rounding_method='HALF-UP')
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit')
            quantity = float_round(ml.quantity, precision_digits=precision_digits, rounding_method='HALF-UP')
            if float_compare(uom_qty, quantity, precision_digits=precision_digits) != 0:
                raise UserError(_('The quantity done for the product "%(product)s" doesn\'t respect the rounding precision '
                                  'defined on the unit of measure "%(unit)s". Please change the quantity done or the '
                                  'rounding precision of your unit of measure.',
                                  product=ml.product_id.display_name, unit=ml.product_uom_id.name))

            qty_done_float_compared = ml.product_uom_id.compare(ml.quantity, 0)
            if qty_done_float_compared > 0:
                if ml.product_id.tracking == 'none':
                    continue
                picking_type_id = ml.move_id.picking_type_id
                if not ml._exclude_requiring_lot():
                    ml_ids_tracked_without_lot.add(ml.id)
                    continue
                if not picking_type_id or ml.lot_id or (not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots):
                    # If the user disabled both `use_create_lots` and `use_existing_lots`
                    # checkboxes on the picking type, he's allowed to enter tracked
                    # products without a `lot_id`.
                    continue
                if picking_type_id.use_create_lots:
                    ml_ids_to_check[(ml.product_id, ml.company_id)].add(ml.id)
                else:
                    ml_ids_tracked_without_lot.add(ml.id)

            elif qty_done_float_compared < 0:
                raise UserError(_('No negative quantities allowed'))
            elif not ml.is_inventory:
                ml_ids_to_delete.add(ml.id)

        for (product, _company), mls in ml_ids_to_check.items():
            mls = self.env['stock.move.line'].browse(mls)
            lots = self.env['stock.lot'].search([
                '|', ('company_id', '=', False), ('company_id', '=', ml.company_id.id),
                ('product_id', '=', product.id),
                ('name', 'in', mls.mapped('lot_name')),
            ])
            lots = {lot.name: lot for lot in lots}
            for ml in mls:
                lot = lots.get(ml.lot_name)
                if lot:
                    ml.lot_id = lot.id
                elif ml.lot_name:
                    ml_ids_to_create_lot.add(ml.id)
                else:
                    ml_ids_tracked_without_lot.add(ml.id)

        if ml_ids_tracked_without_lot:
            mls_tracked_without_lot = self.env['stock.move.line'].browse(ml_ids_tracked_without_lot)
            products_list = "\n".join(f"- {product_name}" for product_name in mls_tracked_without_lot.mapped("product_id.display_name"))
            raise UserError(
                _(
                    "You need to supply a Lot/Serial Number for product:\n%(products)s",
                    products=products_list,
                ),
            )
        if ml_ids_to_create_lot:
            self.env['stock.move.line'].browse(ml_ids_to_create_lot)._create_and_assign_production_lot()

        mls_to_delete = self.env['stock.move.line'].browse(ml_ids_to_delete)
        mls_to_delete.unlink()

        mls_todo = (self - mls_to_delete)
        mls_todo._check_company()

        # Now, we can actually move the quant.
        ml_ids_to_ignore = OrderedSet()
        quants_cache = self.env['stock.quant']._get_quants_by_products_locations(
            mls_todo.product_id, mls_todo.location_id | mls_todo.location_dest_id,
            extra_domain=['|', ('lot_id', 'in', mls_todo.lot_id.ids), ('lot_id', '=', False)])

        # Prepare package history records before any actual move
        if not self.env.context.get('ignore_dest_packages'):
            package_history_vals = mls_todo._prepare_package_history_vals()
            if package_history_vals:
                self.env['stock.package.history'].create(package_history_vals)

        for ml in mls_todo.with_context(quants_cache=quants_cache):
            # if this move line is force assigned, unreserve elsewhere if needed
            ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id, action="reserved", virtual_box=-ml.virtual_box)
            available_qty, in_date = ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id, virtual_box=-ml.virtual_box)
            ml._synchronize_quant(ml.quantity_product_uom, ml.location_dest_id, package=ml.result_package_id, in_date=in_date, virtual_box=-ml.virtual_box)
            if available_qty < 0:
                ml.with_context(quants_cache=None)._free_reservation(
                    ml.product_id, ml.location_id,
                    abs(available_qty), lot_id=ml.lot_id, package_id=ml.package_id,
                    owner_id=ml.owner_id, ml_ids_to_ignore=ml_ids_to_ignore)
            ml_ids_to_ignore.add(ml.id)

        if not self.env.context.get('ignore_dest_packages'):
            mls_todo.result_package_id._apply_dest_to_package()

        # Reset the reserved quantity as we just moved it to the destination location.
        mls_todo.write({
            'date': fields.Datetime.now(),
        })
        
    # def _action_done(self):
    #     """ This method is called during a move's `action_done`. It'll actually move a quant from
    #     the source location to the destination location, and unreserve if needed in the source
    #     location.

    #     This method is intended to be called on all the move lines of a move. This method is not
    #     intended to be called when editing a `done` move (that's what the override of `write` here
    #     is done.
    #     """

    #     # First, we loop over all the move lines to do a preliminary check: `quantity` should not
    #     # be negative and, according to the presence of a picking type or a linked inventory
    #     # adjustment, enforce some rules on the `lot_id` field. If `quantity` is null, we unlink
    #     # the line. It is mandatory in order to free the reservation and correctly apply
    #     # `action_done` on the next move lines.
    #     ml_ids_tracked_without_lot = OrderedSet()
    #     ml_ids_to_delete = OrderedSet()
    #     ml_ids_to_create_lot = OrderedSet()
    #     for ml in self:
    #         # Check here if `ml.quantity` respects the rounding of `ml.product_uom_id`.
    #         uom_qty = float_round(ml.quantity, precision_rounding=ml.product_uom_id.rounding, rounding_method='HALF-UP')
    #         precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #         quantity = float_round(ml.quantity, precision_digits=precision_digits, rounding_method='HALF-UP')
    #         if float_compare(uom_qty, quantity, precision_digits=precision_digits) != 0:
    #             raise UserError(_('The quantity done for the product "%s" doesn\'t respect the rounding precision '
    #                               'defined on the unit of measure "%s". Please change the quantity done or the '
    #                               'rounding precision of your unit of measure.',
    #                               ml.product_id.display_name, ml.product_uom_id.name))

    #         quantity_float_compared = float_compare(ml.quantity, 0, precision_rounding=ml.product_uom_id.rounding)
    #         if quantity_float_compared > 0:
    #             if ml.product_id.tracking != 'none':
    #                 picking_type_id = ml.move_id.picking_type_id
    #                 if picking_type_id:
    #                     if picking_type_id.use_create_lots:
    #                         # If a picking type is linked, we may have to create a production lot on
    #                         # the fly before assigning it to the move line if the user checked both
    #                         # `use_create_lots` and `use_existing_lots`.
    #                         if ml.lot_name and not ml.lot_id:
    #                             lot = self.env['stock.lot'].search([
    #                                 ('company_id', '=', ml.company_id.id),
    #                                 ('product_id', '=', ml.product_id.id),
    #                                 ('name', '=', ml.lot_name),
    #                             ], limit=1)
    #                             if lot:
    #                                 ml.lot_id = lot.id
    #                             else:
    #                                 ml_ids_to_create_lot.add(ml.id)
    #                     elif not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots:
    #                         # If the user disabled both `use_create_lots` and `use_existing_lots`
    #                         # checkboxes on the picking type, he's allowed to enter tracked
    #                         # products without a `lot_id`.
    #                         continue
    #                 elif ml.is_inventory:
    #                     # If an inventory adjustment is linked, the user is allowed to enter
    #                     # tracked products without a `lot_id`.
    #                     continue

    #                 if not ml.lot_id and ml.id not in ml_ids_to_create_lot:
    #                     ml_ids_tracked_without_lot.add(ml.id)
    #         elif quantity_float_compared < 0:
    #             raise UserError(_('No negative quantities allowed'))
    #         elif not ml.is_inventory:
    #             ml_ids_to_delete.add(ml.id)

    #     if ml_ids_tracked_without_lot:
    #         mls_tracked_without_lot = self.env['stock.move.line'].browse(ml_ids_tracked_without_lot)
    #         raise UserError(_('You need to supply a Lot/Serial Number for product: \n - ') +
    #                           '\n - '.join(mls_tracked_without_lot.mapped('product_id.display_name')))
    #     ml_to_create_lot = self.env['stock.move.line'].browse(ml_ids_to_create_lot)
    #     ml_to_create_lot._create_and_assign_production_lot()

    #     mls_to_delete = self.env['stock.move.line'].browse(ml_ids_to_delete)
    #     mls_to_delete.unlink()

    #     mls_todo = (self - mls_to_delete)
    #     mls_todo._check_company()

    #     # Now, we can actually move the quant.
    #     ml_ids_to_ignore = OrderedSet()

    #     for ml in mls_todo:
    #         # if this move line is force assigned, unreserve elsewhere if needed
    #         # ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id, action="reserved", virtual_box=-ml.move_id.virtual_box)
    #         ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id, action="reserved", virtual_box=-ml.virtual_box)
    #         # available_qty, in_date = ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id, virtual_box=-ml.move_id.virtual_box)
    #         available_qty, in_date = ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id, virtual_box=-ml.virtual_box)
    #         # ml._synchronize_quant(ml.quantity_product_uom, ml.location_dest_id, package=ml.result_package_id, in_date=in_date, virtual_box=ml.move_id.virtual_box)
    #         ml._synchronize_quant(ml.quantity_product_uom, ml.location_dest_id, package=ml.result_package_id, in_date=in_date, virtual_box=ml.virtual_box)
    #         if available_qty < 0:
    #             ml._free_reservation(
    #                 ml.product_id, ml.location_id,
    #                 abs(available_qty), lot_id=ml.lot_id, package_id=ml.package_id,
    #                 owner_id=ml.owner_id, ml_ids_to_ignore=ml_ids_to_ignore)
    #         ml_ids_to_ignore.add(ml.id)
    #     # Reset the reserved quantity as we just moved it to the destination location.
    #     mls_todo.write({
    #         'date': fields.Datetime.now(),
    #     })


class StockMove(models.Model):

    _inherit = 'stock.move'

    virtual_box = fields.Integer(
        'Cajas',
        store=True,
        readonly=False,
    )

    def _prepare_procurement_values(self):
        res = super(StockMove,self)._prepare_procurement_values()
        res['virtual_box'] = self.virtual_box
        return res

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):        
        res = super(StockMove,self)._prepare_move_line_vals(quantity, reserved_quant)
        _logger.info('result: %s'%res)
        res['virtual_box'] = self.virtual_box
        return res


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # Reimplementando
    # def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
    #     ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
    #     This function assumes that the given procurement has a rule (action == 'pull' or 'pull_push') set on it.

    #     :param procurement: browse record
    #     :rtype: dictionary
    #     '''
    #     group_id = False
    #     if self.group_propagation_option == 'propagate':
    #         group_id = values.get('group_id', False) and values['group_id'].id
    #     elif self.group_propagation_option == 'fixed':
    #         group_id = self.group_id.id

    #     date_scheduled = fields.Datetime.to_string(
    #         fields.Datetime.from_string(values['date_planned']) - relativedelta(days=self.delay or 0)
    #     )
    #     date_deadline = values.get('date_deadline') and (fields.Datetime.to_datetime(values['date_deadline']) - relativedelta(days=self.delay or 0)) or False
    #     partner = self.partner_address_id or (values.get('group_id', False) and values['group_id'].partner_id)
    #     if partner:
    #         product_id = product_id.with_context(lang=partner.lang or self.env.user.lang)
    #     picking_description = product_id._get_description(self.picking_type_id)
    #     if values.get('product_description_variants'):
    #         picking_description += values['product_description_variants']
    #     # it is possible that we've already got some move done, so check for the done qty and create
    #     # a new move with the correct qty
    #     qty_left = product_qty

    #     move_dest_ids = []
    #     if not self.location_dest_id.should_bypass_reservation():
    #         move_dest_ids = values.get('move_dest_ids', False) and [(4, x.id) for x in values['move_dest_ids']] or []

    #     # when create chained moves for inter-warehouse transfers, set the warehouses as partners
    #     if not partner and move_dest_ids:
    #         move_dest = values['move_dest_ids']
    #         if location_id == company_id.internal_transit_location_id:
    #             partners = move_dest.location_dest_id.warehouse_id.partner_id
    #             if len(partners) == 1:
    #                 partner = partners
    #                 move_dest.partner_id = partner

    #     move_values = {
    #         'name': name[:2000],
    #         'company_id': self.company_id.id or self.location_src_id.company_id.id or self.location_id.company_id.id or company_id.id,
    #         'product_id': product_id.id,
    #         'product_uom': product_uom.id,
    #         'product_uom_qty': qty_left,
    #         'partner_id': partner.id if partner else False,
    #         'location_id': self.location_src_id.id,
    #         'location_dest_id': location_id.id,
    #         'move_dest_ids': move_dest_ids,
    #         'rule_id': self.id,
    #         'procure_method': self.procure_method,
    #         'origin': origin,
    #         'picking_type_id': self.picking_type_id.id,
    #         'group_id': group_id,
    #         'route_ids': [(4, route.id) for route in values.get('route_ids', [])],
    #         'warehouse_id': self.propagate_warehouse_id.id or self.warehouse_id.id,
    #         'date': date_scheduled,
    #         'date_deadline': False if self.group_propagation_option == 'fixed' else date_deadline,
    #         'propagate_cancel': self.propagate_cancel,
    #         'description_picking': picking_description,
    #         'priority': values.get('priority', "0"),
    #         'orderpoint_id': values.get('orderpoint_id') and values['orderpoint_id'].id,
    #         'product_packaging_id': values.get('product_packaging_id') and values['product_packaging_id'].id,
    #         'virtual_box': values.get('virtual_box', 0),
    #     }
    #     for field in self._get_custom_move_fields():
    #         if field in values:
    #             move_values[field] = values.get(field)
    #     return move_values    

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values):
        move_values = super()._get_stock_move_values(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values)
        move_values["virtual_box"] = values.get("virtual_box", 0)
        return move_values


class StockQuant(models.Model):

    _inherit = 'stock.quant'

    virtual_box = fields.Integer('Cajas')

    # Reimplementando
    @api.model
    def _update_available_quantity(
        self,
        product_id,
        location_id,
        quantity=False,
        reserved_quantity=False,
        lot_id=None,
        package_id=None,
        owner_id=None,
        in_date=None,
        virtual_box=False,
    ):
        """ Increase or decrease `quantity` or 'reserved quantity' of a set of quants for a given set of
        product_id/location_id/lot_id/package_id/owner_id.

        :param product_id:
        :param location_id:
        :param quantity:
        :param lot_id:
        :param package_id:
        :param owner_id:
        :param datetime in_date: Should only be passed when calls to this method are done in
                                 order to move a quant. When creating a tracked quant, the
                                 current datetime will be used.
        :return: tuple (available_quantity, in_date as a datetime)
        """
        if not (quantity or reserved_quantity):
            raise ValidationError(_('Quantity or Reserved Quantity should be set.'))
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
        if lot_id:
            if product_id.uom_id.compare(quantity, 0) > 0:
                quants = quants.filtered(lambda q: q.lot_id)
            else:
                # Don't remove quantity from a negative quant without lot
                quants = quants.filtered(lambda q: product_id.uom_id.compare(q.quantity, 0) > 0 or q.lot_id)

        if location_id.should_bypass_reservation():
            incoming_dates = []
        else:
            incoming_dates = [quant.in_date for quant in quants if quant.in_date and
                              quant.product_uom_id.compare(quant.quantity, 0) > 0]
        if in_date:
            incoming_dates += [in_date]
        # If multiple incoming dates are available for a given lot_id/package_id/owner_id, we
        # consider only the oldest one as being relevant.
        if incoming_dates:
            in_date = min(incoming_dates)
        else:
            in_date = fields.Datetime.now()

        quant = None
        if quants:
            # quants are already ordered in _gather
            # lock the first available
            quant = quants.try_lock_for_update(allow_referencing=True, limit=1)

        if quant:
            vals = {"in_date": in_date, "virtual_box": quant.virtual_box + virtual_box}
            if quantity:
                vals['quantity'] = quant.quantity + quantity
            if reserved_quantity:
                vals['reserved_quantity'] = max(0, quant.reserved_quantity + reserved_quantity)
            quant.write(vals)
        else:
            vals = {
                'product_id': product_id.id,
                'location_id': location_id.id,
                'lot_id': lot_id and lot_id.id,
                'package_id': package_id and package_id.id,
                'owner_id': owner_id and owner_id.id,
                'in_date': in_date,
            }
            if quantity:
                vals['quantity'] = quantity
            if reserved_quantity:
                vals['reserved_quantity'] = reserved_quantity
            self.create(vals)
        return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True, allow_negative=True), in_date

    # Extendiendo
    @api.model
    def _get_inventory_fields_write(self):
        res = super()._get_inventory_fields_write()
        res += ["virtual_box"]
        return res
     
    # @api.model
    # def _update_available_quantity(self, product_id, location_id, quantity=False, reserved_quantity=False, lot_id=None,
    #                                package_id=None, owner_id=None, in_date=None, virtual_box=False):
    #     """ Increase or decrease `quantity` or 'reserved quantity' of a set of quants for a given set of
    #     product_id/location_id/lot_id/package_id/owner_id.

    #     :param product_id:
    #     :param location_id:
    #     :param quantity:
    #     :param lot_id:
    #     :param package_id:
    #     :param owner_id:
    #     :param datetime in_date: Should only be passed when calls to this method are done in
    #                              order to move a quant. When creating a tracked quant, the
    #                              current datetime will be used.
    #     :return: tuple (available_quantity, in_date as a datetime)
    #     """
    #     if not (quantity or reserved_quantity):
    #         raise ValidationError(_('Quantity or Reserved Quantity should be set.'))
    #     self = self.sudo()
    #     quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
    #                           strict=True)
    #     if lot_id and quantity > 0:
    #         quants = quants.filtered(lambda q: q.lot_id)

    #     if location_id.should_bypass_reservation():
    #         incoming_dates = []
    #     else:
    #         incoming_dates = [quant.in_date for quant in quants if quant.in_date and
    #                           float_compare(quant.quantity, 0, precision_rounding=quant.product_uom_id.rounding) > 0]
    #     if in_date:
    #         incoming_dates += [in_date]
    #     # If multiple incoming dates are available for a given lot_id/package_id/owner_id, we
    #     # consider only the oldest one as being relevant.
    #     if incoming_dates:
    #         in_date = min(incoming_dates)
    #     else:
    #         in_date = fields.Datetime.now()

    #     quant = None
    #     if quants:
    #         # see _acquire_one_job for explanations
    #         self._cr.execute(
    #             "SELECT id FROM stock_quant WHERE id IN %s ORDER BY lot_id LIMIT 1 FOR NO KEY UPDATE SKIP LOCKED",
    #             [tuple(quants.ids)])
    #         stock_quant_result = self._cr.fetchone()
    #         if stock_quant_result:
    #             quant = self.browse(stock_quant_result[0])

    #     if quant:
    #         vals = {'in_date': in_date, 'virtual_box': quant.virtual_box + virtual_box}
    #         if quantity:
    #             vals['quantity'] = quant.quantity + quantity
    #         if reserved_quantity:
    #             vals['reserved_quantity'] = quant.reserved_quantity + reserved_quantity
    #         quant.write(vals)
    #     else:
    #         vals = {
    #             'product_id': product_id.id,
    #             'location_id': location_id.id,
    #             'lot_id': lot_id and lot_id.id,
    #             'package_id': package_id and package_id.id,
    #             'owner_id': owner_id and owner_id.id,
    #             'in_date': in_date,
    #             'virtual_box': virtual_box
    #         }
    #         if quantity:
    #             vals['quantity'] = quantity
    #         if reserved_quantity:
    #             vals['reserved_quantity'] = reserved_quantity
    #         self.create(vals)
    #     return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id,
    #                                         owner_id=owner_id, strict=False, allow_negative=True), in_date
