# thinq_account_consolidation/models/cashflow_map.py
from odoo import api, fields, models

class ConsolidationCashflowMap(models.Model):
    _name = 'consolidation.cashflow.map'
    _description = 'Cash Flow Mapping (Account/Tag -> Section)'

    def default_txt(self):
        return """
    Cara kerja & aturan yang dipakai

    Balance Sheet

        Klasifikasi pakai account.account.internal_group:

        asset → ASSETS, amount = balance

        liability → LIABILITIES, amount = -balance

        equity → EQUITY, amount = -balance

        Hasil akhirnya menampilkan positif untuk tiap section (mudah dijumlahkan dan dibanding).

    Profit & Loss

        income → REVENUE, amount = -balance (karena income biasanya kredit → balance negatif)

        expense → EXPENSES, amount = +balance

        Sisa akun lain → OTHER (jarang terjadi, bisa diabaikan/ditag ulang).

    Cash Flow

        Pakai konfigurasi mapping (consolidation.cashflow.map) untuk assign akun/tag ke:

        OPERATING / INVESTING / FINANCING

        Dasar sign:

            income → base = -balance

            expense → base = +balance

            lainnya → base = balance

        Lalu dikali sign dari mapping (1 atau -1) bila dibutuhkan (mis. membalik arah arus kas untuk akun tertentu).

        Tanpa mapping, fallback ke OPERATING.

    Eliminating Entries (EE)

        Disiapkan model consolidation.elimination.entry + line.

        EE hanya dipakai saat menghitung konsolidasi (ikut compute_*), tidak mempengaruhi buku standalone.

        Tombol Post/Cancel mempengaruhi apakah line masuk perhitungan (state='posted').

    Hierarki entitas

        Bila kamu sudah punya consolidation.link.descendants(...), engine akan memakainya; kalau belum, engine fallback ke company root saja.
    """
    name    = fields.Char(required=True)
    section = fields.Selection([
        ('OPERATING','Operating'),
        ('INVESTING','Investing'),
        ('FINANCING','Financing'),
    ], required=True, default='OPERATING', index=True)
    account_id = fields.Many2one('account.account', index=True)
    tag_id     = fields.Many2one('account.account.tag', index=True)
    sign       = fields.Integer(default=1, help="1 or -1 to force direction")
    description_use = fields.Text(default=default_txt)

    _sql_constraints = [
        ('unique_target', 'unique(account_id, tag_id)', 'Mapping must be unique per Account/Tag.')
    ]
