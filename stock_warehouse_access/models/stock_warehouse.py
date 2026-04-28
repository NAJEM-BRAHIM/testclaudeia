from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    allowed_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='stock_warehouse_allowed_users_rel',
        column1='warehouse_id',
        column2='user_id',
        string='Usuarios permitidos',
        help='Usuarios con acceso a este almacén. '
             'Si está vacío, ningún usuario (excepto gestores) podrá verlo.',
    )
