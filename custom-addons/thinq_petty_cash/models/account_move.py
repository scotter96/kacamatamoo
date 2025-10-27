from odoo import _, api, fields, models

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    petty_cash_id = fields.Many2one('petty.cash', string='Petty Cash')