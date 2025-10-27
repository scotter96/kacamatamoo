from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ThinqDepositApplyWizard(models.TransientModel):
    _name = 'thinq.deposit.apply.wizard'
    _description = 'Apply Deposit to Invoice/Bill Wizard'

    # Target invoice/bill (readonly)
    move_id = fields.Many2one(
        'account.move',
        string='Invoice/Bill',
        required=True,
        readonly=True
    )
    
    # Partner (readonly) 
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        readonly=True
    )
    
    # Invoice currency (readonly)
    move_type = fields.Selection(
        related='move_id.move_type',
        readonly=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='move_id.currency_id',
        readonly=True
    )

    # Outstanding amount (readonly)
    amount_residual = fields.Monetary(
        string='Outstanding Amount',
        related='move_id.amount_residual',
        currency_field='currency_id',
        readonly=True
    )
    
    # Available deposits (editable)
    deposit_line_ids = fields.One2many(
        'thinq.deposit.apply.line',
        'wizard_id',
        string='Deposit Lines'
    )
    
    total_apply_amount = fields.Monetary(
        string='Total Amount to Apply',
        compute='_compute_total_apply_amount',
        currency_field='currency_id'
    )
    
    @api.depends('deposit_line_ids.apply_amount')
    def _compute_total_apply_amount(self):
        for wizard in self:
            wizard.total_apply_amount = sum(wizard.deposit_line_ids.mapped('apply_amount'))
    
    # Auto-create lines untuk setiap available deposit
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        if self.env.context.get('active_model') == 'account.move' and self.env.context.get('active_id'):
            move = self.env['account.move'].browse(self.env.context['active_id'])
            res.update({
                'move_id': move.id,
                'partner_id': move.partner_id.id,
            })
        elif res.get('move_id'):
            move = self.env['account.move'].browse(res['move_id'])
        else:
            return res
        
        # Get available deposits
        deposit_type = False
        if move.move_type in ['out_invoice', 'out_refund']:
            deposit_type = 'receive'
        elif move.move_type in ['in_invoice', 'in_refund']:
            deposit_type = 'send'
        
        if deposit_type:
            deposits = self.env['thinq.deposit'].search([
                ('partner_id', '=', move.partner_id.id),
                ('type', '=', deposit_type),
                ('state', '=', 'confirmed'),
                ('available_amount', '>', 0)
            ])
            
            deposit_lines = []
            remaining_amount = move.amount_residual
            
            for deposit in deposits:
                if remaining_amount <= 0:
                    break
                    
                # Force refresh computed fields
                deposit.invalidate_recordset(['available_amount', 'used_amount'])
                deposit._compute_available_amount()
                
                # Check available amount again after refresh
                if deposit.available_amount <= 0:
                    continue
                    
                # Convert deposit amount to invoice currency if needed
                apply_amount = 0.0
                if deposit.currency_id == move.currency_id:
                    # Same currency - direct calculation
                    apply_amount = min(deposit.available_amount, remaining_amount)
                else:
                    # Different currency - convert
                    converted_amount = deposit.currency_id._convert(
                        deposit.available_amount,
                        move.currency_id,
                        move.company_id,
                        move.date or fields.Date.context_today(self)
                    )
                    apply_amount = min(converted_amount, remaining_amount)
                
                deposit_lines.append((0, 0, {
                    'deposit_id': deposit.id,
                    'available_amount': deposit.available_amount,  # Current available amount in deposit currency
                    'apply_amount': apply_amount,  # Amount in invoice currency
                }))
                
                remaining_amount -= apply_amount
            
            res['deposit_line_ids'] = deposit_lines
        
        return res
    
    def action_apply_deposits(self):
        """Apply selected deposits to invoice/bill"""
        self.ensure_one()
        
        if not self.deposit_line_ids:
            raise UserError(_('No deposits selected to apply.'))
        
        if self.total_apply_amount <= 0:
            raise UserError(_('Total apply amount must be greater than zero.'))
        
        if self.total_apply_amount > self.amount_residual:
            raise UserError(_('Total apply amount cannot exceed outstanding amount.'))
        
        # Create deposit usage lines
        for line in self.deposit_line_ids.filtered('apply_amount'):
            # Convert apply_amount (in invoice currency) back to deposit currency for validation
            if line.deposit_id.currency_id != self.currency_id:
                amount_in_deposit_currency = self.currency_id._convert(
                    line.apply_amount,
                    line.deposit_id.currency_id,
                    self.move_id.company_id,
                    self.move_id.date or fields.Date.context_today(self)
                )
            else:
                amount_in_deposit_currency = line.apply_amount
            
            # Force refresh computed fields untuk get latest available_amount
            line.deposit_id.invalidate_recordset(['available_amount', 'used_amount'])
            line.deposit_id._compute_available_amount()
            
            # Check validation with proper currency
            if amount_in_deposit_currency > line.deposit_id.available_amount:
                raise UserError(_('Apply amount for %s cannot exceed available amount. Available: %s %s, Trying to apply: %s %s') % (
                    line.deposit_id.name,
                    line.deposit_id.available_amount,
                    line.deposit_id.currency_id.symbol,
                    amount_in_deposit_currency,
                    line.deposit_id.currency_id.symbol
                ))
            
            # Create deposit line
            self.env['thinq.deposit.line'].create({
                'deposit_id': line.deposit_id.id,
                'move_id': self.move_id.id,
                'amount': amount_in_deposit_currency,  # Store in deposit currency
                'notes': f'Applied to {self.move_id.name}'
            })
        
        # Create payment to reduce invoice outstanding
        self._create_deposit_payment()
        
        return {'type': 'ir.actions.act_window_close'}
    
    # Create payment entry to reduce invoice outstanding -> convert apply_amount to company currency
    def _create_deposit_payment(self):
        # Get deposit account based on move type using fallback logic
        deposit_obj = self.env['thinq.deposit']
        
        if self.move_type in ['out_invoice', 'out_refund']:
            # Create dummy deposit object to use the fallback method
            dummy_deposit = deposit_obj.new({
                'company_id': self.move_id.company_id.id,
                'type': 'receive'
            })
            deposit_account = dummy_deposit._get_or_create_deposit_account('customer')
        else:
            # Create dummy deposit object to use the fallback method
            dummy_deposit = deposit_obj.new({
                'company_id': self.move_id.company_id.id,
                'type': 'send'
            })
            deposit_account = dummy_deposit._get_or_create_deposit_account('vendor')
        
        # Convert total_apply_amount to company currency for journal entry
        company_currency = self.move_id.company_id.currency_id
        if self.currency_id != company_currency:
            # Convert invoice currency to company currency
            amount_company_currency = self.currency_id._convert(
                self.total_apply_amount,
                company_currency,
                self.move_id.company_id,
                self.move_id.date or fields.Date.context_today(self)
            )
        else:
            amount_company_currency = self.total_apply_amount
        
        # Create journal entry for payment
        move_vals = {
            'ref': f'Deposit applied to {self.move_id.name}',
            'journal_id': self.move_id.journal_id.id,
            'date': fields.Date.context_today(self),
            'company_id': self.move_id.company_id.id,
            'line_ids': []
        }
        
        # Determine accounts based on invoice/bill type
        if self.move_type in ['out_invoice']:
            # Customer invoice: Debit Customer Deposit, Credit AR
            receivable_account = self.partner_id.property_account_receivable_id
            line_vals = [
                {
                    'name': f'Deposit applied to {self.move_id.name}',
                    'account_id': deposit_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': amount_company_currency,  # Use company currency amount
                    'credit': 0.0,
                },
                {
                    'name': f'Deposit applied to {self.move_id.name}',
                    'account_id': receivable_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': amount_company_currency,  # Use company currency amount
                }
            ]
            
            # Add currency info only if different from company currency
            if self.currency_id != company_currency:
                line_vals[0].update({
                    'currency_id': self.currency_id.id,
                    'amount_currency': self.total_apply_amount,  # Original invoice currency amount
                })
                line_vals[1].update({
                    'currency_id': self.currency_id.id,
                    'amount_currency': -self.total_apply_amount,  # Negative for credit
                })
            
            move_vals['line_ids'] = [(0, 0, line_vals[0]), (0, 0, line_vals[1])]
            
        elif self.move_type in ['in_invoice']:
            # Vendor bill: Debit AP, Credit Vendor Deposit
            payable_account = self.partner_id.property_account_payable_id
            line_vals = [
                {
                    'name': f'Deposit applied to {self.move_id.name}',
                    'account_id': payable_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': amount_company_currency,  # Use company currency amount
                    'credit': 0.0,
                },
                {
                    'name': f'Deposit applied to {self.move_id.name}',
                    'account_id': deposit_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': amount_company_currency,  # Use company currency amount
                }
            ]
            
            # Add currency info only if different from company currency
            if self.currency_id != company_currency:
                line_vals[0].update({
                    'currency_id': self.currency_id.id,
                    'amount_currency': self.total_apply_amount,  # Original invoice currency amount
                })
                line_vals[1].update({
                    'currency_id': self.currency_id.id,
                    'amount_currency': -self.total_apply_amount,  # Negative for credit
                })
            
            move_vals['line_ids'] = [(0, 0, line_vals[0]), (0, 0, line_vals[1])]
        
        # Create and post the move
        payment_move = self.env['account.move'].create(move_vals)
        payment_move.action_post()
        
        # Reconcile with invoice/bill
        if self.move_type in ['out_invoice']:
            # Find lines to reconcile (both should be on receivable account)
            invoice_line = self.move_id.line_ids.filtered(
                lambda l: l.account_id == self.partner_id.property_account_receivable_id and l.debit > 0
            )
            payment_line = payment_move.line_ids.filtered(
                lambda l: l.account_id == self.partner_id.property_account_receivable_id and l.credit > 0
            )
            
        elif self.move_type in ['in_invoice']:
            # Find lines to reconcile (both should be on payable account)
            bill_line = self.move_id.line_ids.filtered(
                lambda l: l.account_id == self.partner_id.property_account_payable_id and l.credit > 0
            )
            payment_line = payment_move.line_ids.filtered(
                lambda l: l.account_id == self.partner_id.property_account_payable_id and l.debit > 0
            )
            invoice_line = bill_line
            
        # Perform reconciliation
        if invoice_line and payment_line:
            (invoice_line + payment_line).reconcile()


class ThinqDepositApplyLine(models.TransientModel):
    _name = 'thinq.deposit.apply.line'
    _description = 'Deposit Apply Line'
    
    wizard_id = fields.Many2one(
        'thinq.deposit.apply.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    deposit_id = fields.Many2one(
        'thinq.deposit',
        string='Deposit',
        required=True
    )
    
    deposit_name = fields.Char(
        related='deposit_id.name',
        readonly=True
    )
    
    deposit_date = fields.Date(
        related='deposit_id.date',
        readonly=True
    )
    
    deposit_currency_id = fields.Many2one(
        'res.currency',
        related='deposit_id.currency_id',
        readonly=True
    )
    
    available_amount = fields.Monetary(
        string='Available Amount',
        currency_field='deposit_currency_id',
        readonly=True
    )
    
    apply_amount = fields.Monetary(
        string='Amount to Apply',
        currency_field='wizard_currency_id'
    )
    
    wizard_currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True
    )
    
    @api.onchange('apply_amount')
    def _onchange_apply_amount(self):
        if self.apply_amount < 0:
            self.apply_amount = 0
        
        # Force refresh computed fields untuk get current available amount
        if self.deposit_id:
            self.deposit_id.invalidate_recordset(['available_amount', 'used_amount'])
            self.deposit_id._compute_available_amount()
            
            # Convert to deposit currency to check limit
            if self.deposit_currency_id != self.wizard_currency_id:
                amount_in_deposit_currency = self.wizard_currency_id._convert(
                    self.apply_amount,
                    self.deposit_currency_id,
                    self.wizard_id.move_id.company_id,
                    self.wizard_id.move_id.date or fields.Date.context_today(self)
                )
            else:
                amount_in_deposit_currency = self.apply_amount
            
            # Check against current available amount
            if amount_in_deposit_currency > self.deposit_id.available_amount:
                # Convert back to wizard currency
                max_apply_amount = self.deposit_currency_id._convert(
                    self.deposit_id.available_amount,
                    self.wizard_currency_id,
                    self.wizard_id.move_id.company_id,
                    self.wizard_id.move_id.date or fields.Date.context_today(self)
                )
                self.apply_amount = max_apply_amount