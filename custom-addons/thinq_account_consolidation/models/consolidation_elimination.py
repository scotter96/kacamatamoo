# thinq_account_consolidation/models/elimination_entries.py
from odoo import api, fields, models

class ConsolidationEliminationEntry(models.Model):
    _name = 'consolidation.elimination.entry'
    _description = 'Consolidation Eliminating Entry'
    _order = 'date desc, id desc'

    name = fields.Char(required=True, default='/')
    date = fields.Date(required=True, default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', required=True)
    line_ids = fields.One2many('consolidation.elimination.line', 'entry_id', copy=True)
    state = fields.Selection([('draft','Draft'),('posted','Posted'),('cancel','Cancelled')], default='draft', index=True)

    source_move_line_ids = fields.Many2many('account.move.line', string='Source Move Lines', readonly=True)

    def action_post(self):
        for r in self:
            r.state = 'posted'

    def action_cancel(self):
        for r in self:
            r.state = 'cancel'

    def action_reset_to_draft(self):
        for r in self:
            r.state = 'draft'


class ConsolidationEliminationLine(models.Model):
    _name = 'consolidation.elimination.line'
    _description = 'Consolidation Eliminating Entry Line'

    entry_id   = fields.Many2one('consolidation.elimination.entry', required=True, ondelete='cascade', index=True)
    date       = fields.Date(related='entry_id.date', store=True)
    state      = fields.Selection(related='entry_id.state', store=True)
    company_id = fields.Many2one(related='entry_id.company_id', comodel_name='res.company', store=True, readonly=True)

    account_id = fields.Many2one('account.account', required=True, index=True)
    name       = fields.Char()
    debit      = fields.Monetary()
    credit     = fields.Monetary()
    balance    = fields.Monetary(compute='_compute_balance', store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True, readonly=True)

    @api.depends('debit','credit')
    def _compute_balance(self):
        for r in self:
            r.balance = (r.debit or 0.0) - (r.credit or 0.0)
