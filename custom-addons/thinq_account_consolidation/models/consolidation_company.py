# Copyright 2011-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):

    _inherit = 'res.company'


    is_consolidation = fields.Boolean(string='Consolidation company')
    subsidiary_link_ids = fields.One2many('consolidation.link', 'parent_id', string='Subsidiaries')
    entity_code = fields.Char('Entity Code', size=10)  # contoh: K001
    # helper: apakah company punya subsidiary aktif pada tanggal hari ini
    has_active_subsidiary = fields.Boolean(
        compute='_compute_has_active_subsidiary', store=False
    )

    def _compute_has_active_subsidiary(self):
        today = fields.Date.context_today(self)
        Link = self.env['consolidation.link']
        for c in self:
            c.has_active_subsidiary = bool(Link.search_count([
                ('parent_id', '=', c.id),
                ('date_from', '<=', today),
                '|', ('date_to', '=', False), ('date_to', '>=', today),
            ]))