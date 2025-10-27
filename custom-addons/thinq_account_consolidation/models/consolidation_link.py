# models/res_company.py
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ConsolidationLink(models.Model):
    """Relasi parent-subsidiary bertanggal (effective dating)."""
    _name = 'consolidation.link'
    _description = 'Consolidation Parent-Child Link'
    _rec_name = 'child_id'
    _order = 'parent_id, child_id, date_from'

    parent_id   = fields.Many2one('res.company', required=True, ondelete='cascade')
    child_id    = fields.Many2one('res.company', required=True, ondelete='restrict',
                                  domain="[('id','!=', parent_id)]")
    date_from   = fields.Date(required=True)
    date_to     = fields.Date()  # optional (open-ended)
    active      = fields.Boolean(default=True)

    _sql_constraints = [
        ('parent_child_unique',
         'unique(parent_id, child_id, date_from, date_to)',
         'This parent/child link already exists for that period.')
    ]

    @api.constrains('parent_id', 'child_id', 'date_from', 'date_to')
    def _check_rules(self):
        for r in self:
            if r.parent_id == r.child_id:
                raise ValidationError(_("Parent and child cannot be the same company."))

            # 1) Child company tidak boleh dipilih oleh parent lain pada periode yang overlap
            overlap = self.search([
                ('id', '!=', r.id),
                ('child_id', '=', r.child_id.id),
                ('active', '=', True),
                ('date_from', '<=', r.date_to or fields.Date.max),
                ('date_to', '>=', r.date_from)  # overlap
            ], limit=1)
            if overlap:
                raise ValidationError(
                    _("Company '%s' already belongs to another parent in the selected period.")
                    % r.child_id.display_name
                )

            # 2) Cegah siklus (A->B, B->A, dst)
            # if r._creates_cycle():
            #     raise ValidationError(_("This link would create a cycle in the hierarchy."))

    def _creates_cycle(self):
        """Simple DFS to ensure no cycles."""
        seen = set()
        stack = [self.parent_id.id]
        while stack:
            parent = stack.pop()
            if parent in seen:
                continue
            seen.add(parent)
            childs = self.search_read([
                ('parent_id', '=', parent),
                ('active', '=', True)
            ], ['child_id'])
            for ch in childs:
                cid = ch['child_id'][0]
                if cid == self.child_id.id:
                    return True
                stack.append(cid)
        return False

    # Helper: ambil semua anak (rekursif) pada tanggal tertentu
    @api.model
    def descendants(self, root_company, on_date, include_self=True):
        ids = set([root_company.id] if include_self else [])
        frontier = [root_company.id]
        while frontier:
            pids = frontier
            frontier = []
            links = self.search([
                ('parent_id', 'in', pids),
                ('active', '=', True),
                ('date_from', '<=', on_date),
                '|', ('date_to', '=', False), ('date_to', '>=', on_date),
            ])
            for l in links:
                if l.child_id.id not in ids:
                    ids.add(l.child_id.id)
                    frontier.append(l.child_id.id)
        return self.env['res.company'].browse(list(ids))
