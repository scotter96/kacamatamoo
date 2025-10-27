# models/consolidated_coa.py
from odoo import api, fields, models

class ConsolidatedCOA(models.Model):
    _name = 'consolidation.coa'
    _description = 'Consolidated Chart of Accounts'
    _rec_name = 'name'

    name        = fields.Char(default=lambda s: 'Consolidated COA', readonly=True)
    company_id  = fields.Many2one('res.company', required=True)
    as_of_date  = fields.Date(required=True, default=fields.Date.context_today)
    line_ids    = fields.One2many('consolidation.coa.line', 'coa_id', readonly=True)
    state       = fields.Selection([('draft','Draft'),('ready','Ready')], default='draft', readonly=True, index=True)

    def action_build(self):
        """Gabungkan COA semua entitas (parent + seluruh anak pada tanggal as_of_date)."""
        Link = self.env['consolidation.link']
        Acc  = self.env['account.account']

        # deteksi field perusahaan pada account.account
        use_company_id = 'company_id' in Acc._fields
        company_field   = 'company_id' if use_company_id else 'company_ids'

        for rec in self:
            companies = Link.descendants(rec.company_id, rec.as_of_date, include_self=True)

            # ambil akun milik salah satu company dalam hierarki
            accounts = Acc.search([(company_field, 'in', companies.ids)])

            # bersihkan baris lama
            rec.line_ids.unlink()
            lines = []

            if use_company_id:
                # mode single-company per akun
                for a in accounts:
                    comp = a.company_id
                    if not comp or comp not in companies:
                        continue
                    code = f"{getattr(comp, 'entity_code', False) or comp.id}-{a.code}-{a.name}"
                    lines.append({
                        'coa_id': rec.id,
                        'company_id': comp.id,
                        'account_id': a.id,
                        'display_code': code,
                    })
            else:
                # mode multi-company (account.company_ids M2M)
                for a in accounts:
                    # hanya company yang termasuk dalam hierarki
                    for comp in (a.company_ids & companies):
                        code = f"{getattr(comp, 'entity_code', False) or comp.id}-{a.code}-{a.name}"
                        lines.append({
                            'coa_id': rec.id,
                            'company_id': comp.id,
                            'account_id': a.id,
                            'display_code': code,
                        })

            if lines:
                self.env['consolidation.coa.line'].create(lines)
            rec.state = 'ready'


class ConsolidatedCOALine(models.Model):
    _name = 'consolidation.coa.line'
    _description = 'Consolidated COA Line'
    _order = 'display_code'

    coa_id       = fields.Many2one('consolidation.coa', required=True, ondelete='cascade', index=True)
    company_id   = fields.Many2one('res.company', required=True, index=True)
    account_id   = fields.Many2one('account.account', required=True, index=True)
    display_code = fields.Char(readonly=True)  # {{EntityCode-COA Code-COA Name}}
