# -*- encoding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    claude_key_enabled = fields.Boolean(
        string="Enable custom Claude API key",
        compute='_compute_claude_key_enabled',
        readonly=False,
        groups='base.group_system',
    )
    claude_key = fields.Char(
        string="Claude API key",
        config_parameter='ai.claude_key',
        readonly=False,
        groups='base.group_system',
    )

    def _compute_claude_key_enabled(self):
        for record in self:
            record.claude_key_enabled = bool(record.claude_key)