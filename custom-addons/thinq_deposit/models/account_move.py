from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Field untuk track deposit yang digunakan
    deposit_line_ids = fields.One2many(
        'thinq.deposit.line',
        'move_id',
        string='Applied Deposits'
    )
    
    total_deposit_applied = fields.Monetary(
        string='Total Deposit Applied',
        compute='_compute_deposit_amounts',
        currency_field='currency_id'
    )
    
    available_deposits = fields.One2many(
        'thinq.deposit',
        compute='_compute_available_deposits',
        string='Available Deposits'
    )
    
    @api.depends('deposit_line_ids.amount')
    def _compute_deposit_amounts(self):
        for move in self:
            move.total_deposit_applied = sum(move.deposit_line_ids.mapped('amount'))
    
    @api.depends('partner_id', 'move_type')
    def _compute_available_deposits(self):
        for move in self:
            if not move.partner_id:
                move.available_deposits = self.env['thinq.deposit']
                continue
            
            # Tentukan type deposit berdasarkan move_type
            deposit_type = False
            if move.move_type in ['out_invoice', 'out_refund']:  # Customer Invoice
                deposit_type = 'receive'
            elif move.move_type in ['in_invoice', 'in_refund']:  # Vendor Bill
                deposit_type = 'send'
            
            if deposit_type:
                deposits = self.env['thinq.deposit'].search([
                    ('partner_id', '=', move.partner_id.id),
                    ('type', '=', deposit_type),
                    ('state', '=', 'confirmed'),
                    ('available_amount', '>', 0)
                ])
                move.available_deposits = deposits
            else:
                move.available_deposits = self.env['thinq.deposit']
    
    def action_apply_deposit(self):
        """Open wizard untuk apply deposit"""
        if not self.partner_id:
            raise UserError(_('Partner is required to apply deposit.'))
        
        # Check available deposits
        if not self.available_deposits:
            deposit_type_name = 'Customer Deposits' if self.move_type in ['out_invoice', 'out_refund'] else 'Vendor Deposits'
            raise UserError(_('No available %s found for %s.') % (deposit_type_name, self.partner_id.name))
        
        # Launch wizard dengan smart context
        return {
            'name': _('Apply Deposit'),
            'type': 'ir.actions.act_window',
            'res_model': 'thinq.deposit.apply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }