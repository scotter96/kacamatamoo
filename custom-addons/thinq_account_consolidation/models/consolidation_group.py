# models/consolidation_group.py
from odoo import api, fields, models


class ConsolidationGroupingGroup(models.Model):
    _name = 'consolidation.group'
    _description = 'Consolidation Group'

    name = fields.Char()
    parent_id = fields.Many2one(
        comodel_name='consolidation.group',
        string='Parent Group',
    )
    child_ids = fields.One2many(
        comodel_name='consolidation.group',
        inverse_name='parent_id',
        string='Sub Group'
    )
