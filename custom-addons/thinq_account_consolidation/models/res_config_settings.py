# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'


    is_consolidation = fields.Boolean(
        string='Consolidation company',
        related='company_id.is_consolidation',
        help='Check this box if you want to consolidate in this company.',
        readonly=False,
    )
  