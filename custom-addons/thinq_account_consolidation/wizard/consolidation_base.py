# thinq_account_consolidation/wizard/consolidated_report_wizard.py
from odoo import api, fields, models

class ConsolidatedReportWizard(models.TransientModel):
    _name = 'consolidated.report.wizard'
    _description = 'Consolidated Report Wizard'

    root_company_id = fields.Many2one('res.company', required=True)
    date_from = fields.Date(required=True)
    date_to   = fields.Date(required=True)
    favourite_name = fields.Char('Save as Favourite')
    
    def action_generate_eliminations(self):
        self.ensure_one()
        engine = self.env['consolidation.engine'].sudo()
        entry = engine.generate_eliminations(self.root_company_id, self.date_from, self.date_to)
        if entry:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Eliminating Entry'),
                'res_model': 'consolidation.elimination.entry',
                'view_mode': 'form',
                'res_id': entry.id,
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}


    def _build_results(self, title, statement):
        self.ensure_one()
        engine = self.env['consolidation.engine']
        if statement == 'BS':
            matrix = engine.compute_balance_sheet(self.root_company_id, self.date_from, self.date_to)
        elif statement == 'PL':
            matrix = engine.compute_profit_loss(self.root_company_id, self.date_from, self.date_to)
        else:
            matrix = engine.compute_cash_flow(self.root_company_id, self.date_from, self.date_to)

        Result = self.env['consolidated.report.result'].sudo()
        Result.search([('wizard_id', '=', self.id)]).unlink()

        payload = []
        for r in matrix:
            r.update({
                'wizard_id': self.id,
                'title'    : f'Consolidated {title}',
                'root_company_id': self.root_company_id.id,
                'date_from': self.date_from,
                'date_to'  : self.date_to,
                'section'  : r.get('section'),
                'statement': r.get('statement'),
                'amount'   : r.get('amount'),
            })
            payload.append(r)
        if payload:
            Result.create(payload)

    def _open_result(self, title, statement):
        self._build_results(title, statement)
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : f'Consolidated {title}',
            'res_model': 'consolidated.report.result',
            'view_mode': 'pivot,tree,graph',
            'domain'   : [('wizard_id', '=', self.id)],
            'target'   : 'current',
            'context'  : {'group_by': ['section','company_id', 'account_id']},
        }

    def action_open_balance_sheet(self):
        return self._open_result('Balance Sheet', 'BS')

    def action_open_profit_loss(self):
        return self._open_result('Profit & Loss', 'PL')

    def action_open_cashflow(self):
        return self._open_result('Cash Flow', 'CF')
