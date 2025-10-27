# models/elimination_rule.py
from odoo import api, fields, models

class ConsolidationEliminationRule(models.Model):
    _name = 'consolidation.elimination.rule'
    _description = 'Elimination Rule'

    name = fields.Char(required=True)
    parent_company_id = fields.Many2one('res.company', required=True, help="Root consolidation company where this rule applies")
    active = fields.Boolean(default=True)

    # tipe rule: 'intercompany_arap', 'intercompany_rev_cogs', dst.
    rule_type = fields.Selection([
        ('intercompany_arap', 'Intercompany AR/AP'),
        ('intercompany_rev_cogs', 'Intercompany Revenue/COGS'),
        ('intercompany_loans', 'Intercompany Loans'),
        ('dividend', 'Dividend'),
        ('inventory_up', 'Unrealized Profit in Inventory'),
    ], required=True, default='intercompany_arap')

    # Akun kontra yang dipakai di parent consolidation
    account_ic_ar = fields.Many2one('account.account', string="Contra A/R (Parent)")
    account_ic_ap = fields.Many2one('account.account', string="Contra A/P (Parent)")
    account_ic_rev = fields.Many2one('account.account', string="Contra Revenue (Parent)")
    account_ic_cogs = fields.Many2one('account.account', string="Contra COGS (Parent)")

    # Filter tambahan opsional
    use_partner_map = fields.Boolean(default=True, help="Match intercompany by partner == subsidiary's partner_id")

    note = fields.Text()
