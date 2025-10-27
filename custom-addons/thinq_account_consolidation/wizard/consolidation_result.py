# thinq_account_consolidation/models/consolidated_report_result.py
from odoo import api, fields, models

class ConsolidatedReportResult(models.TransientModel):
    _name = 'consolidated.report.result'
    _description = 'Consolidated Report Result'
    _rec_name = 'account_code'

    wizard_id        = fields.Many2one('consolidated.report.wizard', ondelete='cascade', index=True)
    title            = fields.Char()
    root_company_id  = fields.Many2one('res.company')
    date_from        = fields.Date()
    date_to          = fields.Date()

    statement = fields.Selection([('BS','Balance Sheet'),('PL','Profit & Loss'),('CF','Cash Flow')], index=True)
    section   = fields.Char(index=True)

    company_id   = fields.Many2one('res.company', index=True)
    company_code = fields.Char(index=True)

    account_id   = fields.Many2one('account.account', index=True)
    account_code = fields.Char(index=True)
    account_name = fields.Char()

    # angka mentah AML
    debit   = fields.Monetary(currency_field='company_currency_id')
    credit  = fields.Monetary(currency_field='company_currency_id')
    balance = fields.Monetary(currency_field='company_currency_id')

    # angka “report” setelah normalisasi/sign untuk section/statement
    amount  = fields.Monetary(currency_field='company_currency_id')

    company_currency_id = fields.Many2one('res.currency', compute='_compute_currency', readonly=True)

    @api.depends('company_id')
    def _compute_currency(self):
        for rec in self:
            rec.company_currency_id = rec.company_id.currency_id.id if rec.company_id else self.env.company.currency_id.id
