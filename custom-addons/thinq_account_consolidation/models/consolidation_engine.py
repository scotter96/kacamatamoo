# thinq_account_consolidation/models/consolidation_engine.py
from odoo import api, fields, models, _
from collections import defaultdict
from datetime import date, datetime

class ConsolidationEngine(models.AbstractModel):
    _name = 'consolidation.engine'
    _description = 'Consolidation Compute Engine'

    # --------------------------
    # ========== HELPERS =======
    # --------------------------
    @api.model
    def _get_descendants(self, root_company, at_date=None, include_self=True):
        """
        Kembalikan semua company anak (berdasarkan consolidation.link) + parent-nya jika include_self.
        Kalau kamu belum punya model consolidation.link, fallback hanya root_company.
        """
        if 'consolidation.link' in self.env:
            return self.env['consolidation.link'].descendants(root_company, at_date, include_self=include_self)
        return root_company

    @api.model
    def _domain_base_period(self, companies, date_from, date_to):
        domain = [('parent_state', '=', 'posted')]
        if companies:
            domain.append(('company_id', 'in', companies.ids))
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        return domain

    @api.model
    def _pull_posted_move_lines(self, companies, date_from, date_to):
        """
        Ambil account.move.line posted dalam periode dan perusahaan yang relevan.
        Fields: company_id, account_id, debit, credit, balance
        """
        AML = self.env['account.move.line'].sudo()
        domain = self._domain_base_period(companies, date_from, date_to)
        fields_to_read = ['company_id', 'account_id', 'debit', 'credit', 'balance']
        return AML.search_read(domain, fields_to_read, limit=0)

    @api.model
    def _bucket_by_company_account(self, records):
        """
        records: list of dict (company_id, account_id, debit, credit, balance)
        return: {(company_id, account_id): {'debit':..,'credit':..,'balance':..}}
        """
        bucket = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0, 'balance': 0.0})
        for l in records:
            comp_id = l['company_id'][0] if isinstance(l.get('company_id'), (list, tuple)) else l.get('company_id')
            acc_id  = l['account_id'][0]  if isinstance(l.get('account_id'), (list, tuple)) else l.get('account_id')
            if not comp_id or not acc_id:
                continue
            key = (comp_id, acc_id)
            bucket[key]['debit']   += float(l.get('debit', 0.0))
            bucket[key]['credit']  += float(l.get('credit', 0.0))
            bucket[key]['balance'] += float(l.get('balance', 0.0))
        return bucket

    @api.model
    def _company_account_maps(self, comp_ids, acc_ids):
        companies_map = {c.id: c for c in self.env['res.company'].browse(list(comp_ids))}
        accounts_map  = {a.id: a for a in self.env['account.account'].browse(list(acc_ids))}
        return companies_map, accounts_map

    # --------------------------
    # ====== CORE COMPUTE ======
    # --------------------------
    @api.model
    def compute_raw_matrix(self, root_company, date_from, date_to, include_elimination=True):
        """
        Matrix dasar per company & account (debit, credit, balance) => termasuk EE (jika diminta).
        """
        companies = self._get_descendants(root_company, at_date=date_to, include_self=True)

        aml = self._pull_posted_move_lines(companies, date_from, date_to)
        bucket = self._bucket_by_company_account(aml)

        if include_elimination:
            ee = self._pull_elimination_lines(companies, date_from, date_to)
            ee_bucket = self._bucket_by_company_account(ee)
            for key, vals in ee_bucket.items():
                bucket[key]['debit']   += vals['debit']
                bucket[key]['credit']  += vals['credit']
                bucket[key]['balance'] += vals['balance']

        comp_ids = {k[0] for k in bucket.keys()}
        acc_ids  = {k[1] for k in bucket.keys()}
        companies_map, accounts_map = self._company_account_maps(comp_ids, acc_ids)

        rows = []
        for (comp_id, acc_id), vals in bucket.items():
            comp = companies_map.get(comp_id)
            acc  = accounts_map.get(acc_id)
            rows.append({
                'company_id'  : comp_id,
                'company_code': getattr(comp, 'entity_code', False) or str(comp_id),
                'account_id'  : acc_id,
                'account_code': acc.code if acc else '',
                'account_name': acc.name if acc else '',
                'internal_group': acc.internal_group if acc else '',  # 'asset','liability','equity','income','expense','off_balance'
                'debit'       : vals['debit'],
                'credit'      : vals['credit'],
                'balance'     : vals['balance'],  # Odoo: debit - credit
            })
        return rows

    # --------------------------
    # ==== STATEMENT LOGICS ====
    # --------------------------
    @api.model
    def _map_bs_section(self, internal_group):
        """
        Mapping formal Balance Sheet per internal_group
        """
        if internal_group == 'asset':
            return 'ASSETS'
        if internal_group in ('liability',):
            return 'LIABILITIES'
        if internal_group in ('equity',):
            return 'EQUITY'
        return 'OTHER'

    @api.model
    def _normalize_amount_bs(self, row):
        """
        BS: tampilkan aset sebagai positif (balance), liabilities & equity juga positif secara presentasi.
        Karena balance = debit - credit, maka:
          - asset      : amount =  balance
          - liability  : amount = -balance (agar kewajiban tampil positif)
          - equity     : amount = -balance (agar ekuitas tampil positif)
        """
        grp = row.get('internal_group')
        bal = row.get('balance', 0.0)
        if grp == 'asset':
            return bal
        if grp in ('liability', 'equity'):
            return -bal
        return bal

    @api.model
    def compute_balance_sheet(self, root_company, date_from, date_to):
        rows = self.compute_raw_matrix(root_company, date_from, date_to, include_elimination=True)
        out = []
        for r in rows:
            section = self._map_bs_section(r.get('internal_group'))
            amount  = self._normalize_amount_bs(r)
            out.append({**r, 'statement': 'BS', 'section': section, 'amount': amount})
        return out

    @api.model
    def _map_pl_section(self, internal_group):
        """
        P&L: Group utama: REVENUE vs EXPENSES
        """
        if internal_group == 'income':
            return 'REVENUE'
        if internal_group == 'expense':
            return 'EXPENSES'
        return 'OTHER'

    @api.model
    def _normalize_amount_pl(self, row):
        """
        P&L: revenue ingin tampil POSITIF (padahal balance income biasanya negatif),
             expense tampil POSITIF juga (untuk subtotal), tinggal di-compare di laporan akhir.
        - income  : amount = -balance  (agar naik = nilai positif)
        - expense : amount =  balance  (agar beban = nilai positif)
        """
        grp = row.get('internal_group')
        bal = row.get('balance', 0.0)
        if grp == 'income':
            return -bal
        if grp == 'expense':
            return bal
        return bal

    @api.model
    def compute_profit_loss(self, root_company, date_from, date_to):
        rows = self.compute_raw_matrix(root_company, date_from, date_to, include_elimination=True)
        out = []
        for r in rows:
            section = self._map_pl_section(r.get('internal_group'))
            amount  = self._normalize_amount_pl(r)
            out.append({**r, 'statement': 'PL', 'section': section, 'amount': amount})
        return out

    @api.model
    def _get_cf_section_by_mapping(self, account):
        """
        Cari mapping Cash Flow berbasis konfigurasi:
        - Level 1: mapping spesifik account
        - Level 2: mapping by account.tag
        - Fallback: OPERATING
        """
        section = 'OPERATING'
        CFMap = self.env['consolidation.cashflow.map'].sudo() if 'consolidation.cashflow.map' in self.env else None
        if not CFMap or not account:
            return section
        # account mapping
        rec = CFMap.search([('account_id', '=', account.id)], limit=1)
        if rec:
            return rec.section
        # tag mapping
        if account.tag_ids:
            rec = CFMap.search([('tag_id', 'in', account.tag_ids.ids)], limit=1)
            if rec:
                return rec.section
        return section

    @api.model
    def _normalize_amount_cf(self, row):
        """
        Cash Flow dasar: gunakan balance seperti P&L (income -> -bal, expense -> +bal), 
        lalu CF mapping menetapkan sign tambahan via config (field 'sign': 1 atau -1).
        """
        grp = row.get('internal_group')
        bal = row.get('balance', 0.0)
        if grp == 'income':
            base = -bal
        elif grp == 'expense':
            base = bal
        else:
            base = bal
        return base

    @api.model
    def compute_cash_flow(self, root_company, date_from, date_to):
        rows = self.compute_raw_matrix(root_company, date_from, date_to, include_elimination=True)
        # siapkan peta akun utk cari mapping CF
        acc_ids = list({r['account_id'] for r in rows})
        acc_map = {a.id: a for a in self.env['account.account'].browse(acc_ids)}

        out = []
        # optional mapping sign
        sign_map = {}
        if 'consolidation.cashflow.map' in self.env:
            for m in self.env['consolidation.cashflow.map'].sudo().search([]):
                key = ('acc', m.account_id.id) if m.account_id else ('tag', m.tag_id.id)
                sign_map[key] = m.sign if m.sign else 1

        for r in rows:
            acc = acc_map.get(r['account_id'])
            section = self._get_cf_section_by_mapping(acc)  # OPERATING / INVESTING / FINANCING
            amount  = self._normalize_amount_cf(r)

            # apply sign config bila ada
            sig = 1
            if acc:
                if ('acc', acc.id) in sign_map:
                    sig = sign_map[('acc', acc.id)]
                else:
                    tag_hit = next((sign_map[('tag', t.id)] for t in acc.tag_ids if ('tag', t.id) in sign_map), None)
                    if tag_hit is not None:
                        sig = tag_hit
            amount *= sig

            out.append({**r, 'statement': 'CF', 'section': section, 'amount': amount})
        return out
    
    # Ambil semua entitas dalam pohon konsolidasi
    def _get_tree_company_ids(self, parent_company, as_of=None):
        Link = self.env['consolidation.link']
        companies = Link.descendants(parent_company, as_of or fields.Date.context_today(self))
        return companies.ids

    def _company_partner_id_map(self, company_ids):
        # map: company_id -> partner_id perusahaan tsb (untuk match intercompany)
        companies = self.env['res.company'].browse(company_ids)
        return {c.id: c.partner_id.id for c in companies if c.partner_id}

    @api.model
    def _pull_elimination_lines(self, companies, date_from, date_to):
        """
        Ambil Eliminating Entries yang 'posted' dalam periode & perusahaan terkait.
        """
        model_name = 'consolidation.elimination.line'
        if model_name not in self.env:
            return []
        EL = self.env[model_name].sudo()
        domain = [('entry_id.state', '=', 'posted')]
        if companies:
            domain.append(('company_id', 'in', companies.ids))
        if date_from:
            domain.append(('entry_id.date', '>=', date_from))
        if date_to:
            domain.append(('entry_id.date', '<=', date_to))
        fields_to_read = ['company_id', 'account_id', 'debit', 'credit', 'balance']
        return EL.search_read(domain, fields_to_read, limit=0)

    # -------------------------------
    # 2.1 Generator: Intercompany AR/AP
    # -------------------------------
    @api.model
    def generate_eliminations(self, parent_company, date_from, date_to):
        """Generate satu Eliminating Entry (AR/AP intercompany) untuk periode."""
        Rule  = self.env['consolidation.elimination.rule'].sudo()
        Entry = self.env['consolidation.elimination.entry'].sudo()
        ELine = self.env['consolidation.elimination.line'].sudo()
        AML   = self.env['account.move.line'].sudo()

        rule = Rule.search([
            ('parent_company_id', '=', parent_company.id),
            ('active', '=', True),
            ('rule_type', '=', 'intercompany_arap'),
        ], limit=1)
        if not rule:
            return False

        tree_ids = self._get_tree_company_ids(parent_company, as_of=date_to)
        if not tree_ids:
            return False

        comp2partner = self._company_partner_id_map(tree_ids)

        aml_domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', 'in', tree_ids),
            ('parent_state', '=', 'posted'),
            ('account_type', 'in', ['asset_receivable', 'liability_payable']),
            ('balance', '!=', 0.0),
            ('partner_id', '!=', False),
        ]
        fields_needed = ['company_id', 'partner_id', 'account_id', 'balance', 'currency_id', 'date']
        lines = AML.with_context(prefetch_fields=False).search_read(aml_domain, fields=fields_needed, limit=0)
        if not lines:
            return False

        # build partner->company reverse map
        partner2company = {p_id: c_id for c_id, p_id in comp2partner.items()}

        from collections import defaultdict as dd
        pair_sum = dd(float)
        source_line_ids = []
        for l in lines:
            src_cid = l['company_id'][0]
            dst_cid = partner2company.get(l['partner_id'][0])
            if not dst_cid or dst_cid == src_cid:
                continue
            pair_sum[(src_cid, dst_cid)] += float(l.get('balance', 0.0))
            if 'id' in l:
                source_line_ids.append(l['id'])

        if not pair_sum:
            return False

        entry = Entry.create({
            'name': _("EE Intercompany AR/AP %s - %s") % (date_from, date_to),
            'parent_company_id': parent_company.id,
            'date_from': date_from,
            'date_to': date_to,
            'rule_id': rule.id,
            'auto_generated': True,
        })
        if source_line_ids:
            entry.write({'source_move_line_ids': [(6, 0, source_line_ids)]})

        lines_to_create = []
        for (src_cid, dst_cid), amount in pair_sum.items():
            if abs(amount) < 1e-6:
                continue
            label = f"Eliminate IC AR/AP between C{src_cid} and C{dst_cid} ({date_from}..{date_to})"

            if amount > 0:
                # AR di src -> Cr contra AR, Dr contra AP
                if not (rule.account_ic_ar and rule.account_ic_ap):
                    continue
                lines_to_create += [
                    {'entry_id': entry.id, 'company_id': parent_company.id,
                     'account_id': rule.account_ic_ar.id, 'label': label, 'credit': amount, 'debit': 0.0},
                    {'entry_id': entry.id, 'company_id': parent_company.id,
                     'account_id': rule.account_ic_ap.id, 'label': label, 'debit': amount, 'credit': 0.0},
                ]
            else:
                amt = -amount
                if not (rule.account_ic_ar and rule.account_ic_ap):
                    continue
                lines_to_create += [
                    {'entry_id': entry.id, 'company_id': parent_company.id,
                     'account_id': rule.account_ic_ar.id, 'label': label, 'debit': amt, 'credit': 0.0},
                    {'entry_id': entry.id, 'company_id': parent_company.id,
                     'account_id': rule.account_ic_ap.id, 'label': label, 'credit': amt, 'debit': 0.0},
                ]

        if lines_to_create:
            ELine.create(lines_to_create)
            return entry
        entry.unlink()
        return False
    
    # --------------------------------
    # 2.2 Dipakai oleh wizard laporan
    # --------------------------------
    def compute_matrix(self, parent_company, date_from, date_to):
        """Kembalikan matriks konsolidasi: JE + EE sesuai Acceptance Criteria."""
        Link = self.env['consolidation.link']
        tree_ids = self._get_tree_company_ids(parent_company, as_of=date_to)
        if parent_company.id not in tree_ids:
            tree_ids.append(parent_company.id)

        # 1) Ambil saldo JE (GL) per perusahaan, akun
        AML = self.env['account.move.line']
        gl_rows = AML.read_group(
            domain=[
                ('date', '>=', date_from), ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
                ('company_id', 'in', tree_ids),
            ],
            fields=['company_id', 'account_id', 'balance:sum'],
            groupby=['company_id', 'account_id'],
            lazy=False
        )

        # 2) Tambahkan EE (eliminating entries) periode — gunakan model kita
        EE = self.env['consolidation.elimination.entry']
        ee_lines = self.env['consolidation.elimination.line'].search_read([
            ('entry_id.parent_company_id', '=', parent_company.id),
            ('entry_id.date_from', '=', date_from),
            ('entry_id.date_to', '=', date_to),
            ('entry_id.state', 'in', ['draft','posted']),
        ], ['company_id', 'account_id', 'debit', 'credit'])

        # Build matrix: key=(company_id, account_id) -> amount
        from collections import defaultdict
        matrix = defaultdict(float)

        for r in gl_rows:
            if r.get('company_id') and r.get('account_id'):
                c = r['company_id'][0]
                a = r['account_id'][0]
                matrix[(c, a)] += r.get('balance_sum', 0.0)

        for l in ee_lines:
            c = l['company_id'][0]
            a = l['account_id'][0]
            matrix[(c, a)] += (l.get('debit', 0.0) - l.get('credit', 0.0))

        # Return sebagai list agar mudah dipakai di report result
        res = []
        Account = self.env['account.account'].browse(list({a for (_, a) in matrix.keys()}))
        acc_map = {a.id: a for a in Account}
        Company = self.env['res.company'].browse(list({c for (c, _) in matrix.keys()}))
        comp_map = {c.id: c for c in Company}

        for (cid, aid), amt in matrix.items():
            if abs(amt) < 1e-8:
                continue
            a = acc_map.get(aid)
            c = comp_map.get(cid)
            res.append({
                'company_id': cid,
                'company_name': c and c.display_name or str(cid),
                'account_id': aid,
                'account_code': a and a.code or '',
                'account_name': a and a.name or '',
                'amount': amt,
            })
        return res
