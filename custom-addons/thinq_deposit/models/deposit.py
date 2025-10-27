from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ThinqDeposit(models.Model):
    _name = 'thinq.deposit'
    _description = 'Thinq Deposit Management'
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        help="Customer (for receive) or Vendor (for send)"
    )

    type = fields.Selection([
        ('receive', 'Receive (From Customer)'),
        ('send', 'Send (To Vendor)')
    ], string='Type', required=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True
    )
    
    amount_company_currency = fields.Monetary(
        string='Amount in Company Currency',
        currency_field='company_currency_id',
        compute='_compute_amount_company_currency',
        store=True
    )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Company Currency'
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('used', 'Fully Used'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    available_amount = fields.Monetary(
        string='Available Amount',
        currency_field='currency_id',
        compute='_compute_available_amount',
        store=True
    )
    
    used_amount = fields.Monetary(
        string='Used Amount',
        currency_field='currency_id',
        compute='_compute_available_amount',
        store=True
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        domain="[('company_id', '=', company_id), ('type', 'in', ['bank', 'cash'])]"
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False
    )
    
    deposit_line_ids = fields.One2many(
        'thinq.deposit.line',
        'deposit_id',
        string='Usage Lines'
    )
    
    notes = fields.Text(string='Notes')
    
    # untuk convert foreign currency ke company currency yang digunakan
    @api.depends('currency_id', 'amount', 'company_currency_id', 'date')
    def _compute_amount_company_currency(self):
        for record in self:
            if record.currency_id and record.company_currency_id:
                if record.currency_id == record.company_currency_id:
                    record.amount_company_currency = record.amount
                else:
                    record.amount_company_currency = record.currency_id._convert(
                        record.amount,
                        record.company_currency_id,
                        record.company_id,
                        record.date or fields.Date.context_today(record)
                    )
            else:
                record.amount_company_currency = record.amount
    
    @api.depends('deposit_line_ids.amount')
    def _compute_available_amount(self):
        for record in self:
            # hitung total amount yang sudah digunakan
            used_amount = sum(record.deposit_line_ids.mapped('amount'))
            record.used_amount = used_amount

            # available amount = total amount - used amount
            record.available_amount = record.amount - used_amount
            
            # Update state based on usage
            if record.state == 'confirmed':
                if record.available_amount <= 0:
                    record.state = 'used'
    
    # auto generate reference number 
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            sequence_code = 'thinq.deposit.receive' if vals.get('type') == 'receive' else 'thinq.deposit.send'
            vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code) or 'New'
        return super().create(vals)
    
    # klik confirm > panggil function create jurnal entry
    def action_confirm(self):
        """Confirm deposit and create journal entry"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft deposits can be confirmed.'))
            
            if not record.journal_id:
                raise UserError(_('Please select a journal.'))
            
            # Create journal entry
            record._create_journal_entry()
            record.state = 'confirmed'
    
    # klik cancel ketika sudah konfirm, maka cek kl sdh kepakai, gabisa cancel
    def action_cancel(self):
        """Cancel deposit"""
        for record in self:
            if record.used_amount > 0:
                raise UserError(_('Cannot cancel a deposit that has been used.'))
            
            if record.move_id:
                record.move_id.button_cancel()
                record.move_id.unlink() # Hapus jurnal entry jika ada
            
            record.state = 'cancelled'

    # ambil atau buat deposit account
    def _get_or_create_deposit_account(self, account_type):
        """Get or create deposit account based on type with fallback logic"""
        company = self.company_id
        
        if account_type == 'customer':
            # Cek apakah sudah ada account di company settings
            account = company.account_customer_deposit_id
            if not account:
                # Cari account yang sudah ada dengan nama yang mengandung "deposit"
                account = self.env['account.account'].search([
                    ('account_type', '=', 'liability_current'),
                    '|', ('name', 'ilike', 'deposit'), ('name', 'ilike', 'customer deposit')
                ], limit=1)
                
                if not account:
                    # Cari account liability yang bisa dipakai
                    account = self.env['account.account'].search([
                        ('account_type', '=', 'liability_current'),
                        ('code', 'like', '2%')  # Account code yang dimulai dengan 2 (liability)
                    ], limit=1)
                    
                    if not account:
                        # Buat account baru jika benar-benar tidak ada
                        try:
                            account = self.env['account.account'].create({
                                'code': self._generate_account_code('2110'),
                                'name': 'Customer Deposits',
                                'account_type': 'liability_current',
                                'reconcile': True
                            })
                        except Exception as e:
                            raise UserError(_('Cannot create Customer Deposit account. Please create account manually with type "Current Liabilities". Error: %s') % str(e))
                
                # Set sebagai default di company
                try:
                    company.sudo().write({'account_customer_deposit_id': account.id})
                except:
                    # Jika tidak bisa write ke company, skip saja
                    pass
                    
        else:  # vendor
            # Cek apakah sudah ada di company settings
            account = company.account_vendor_deposit_id
            if not account:
                # Cari account yang sudah ada dengan nama yang mengandung "deposit"
                account = self.env['account.account'].search([
                    ('account_type', '=', 'asset_current'),
                    '|', ('name', 'ilike', 'deposit'), ('name', 'ilike', 'vendor deposit')
                ], limit=1)
                
                if not account:
                    # Cari account asset yang bisa dipakai
                    account = self.env['account.account'].search([
                        ('account_type', '=', 'asset_current'),
                        ('code', 'like', '1%')  # Account code yang dimulai dengan 1 (asset)
                    ], limit=1)
                    
                    if not account:
                        # Buat account baru jika benar-benar tidak ada
                        try:
                            account = self.env['account.account'].create({
                                'code': self._generate_account_code('1140'),
                                'name': 'Vendor Deposits',
                                'account_type': 'asset_current',
                                'reconcile': True
                            })
                        except Exception as e:
                            raise UserError(_('Cannot create Vendor Deposit account. Please create account manually with type "Current Assets". Error: %s') % str(e))
                
                # Set sebagai default di company
                try:
                    company.sudo().write({'account_vendor_deposit_id': account.id})
                except:
                    # Jika tidak bisa write ke company, skip saja
                    pass
        
        return account

    # Generate unique account code
    def _generate_account_code(self, preferred_code):
        """Generate unique account code"""        
        # Cek apakah preferred code sudah dipakai
        existing = self.env['account.account'].search([
            ('code', '=', preferred_code)
        ])
        
        if not existing:
            return preferred_code
        
        # Jika sudah ada, generate code baru increment: 2110 → 2111, 2112, ...
        base_code = preferred_code[:3]  # Ambil 3 digit pertama
        for i in range(1, 100):
            new_code = f"{base_code}{i}"
            existing = self.env['account.account'].search([
                ('code', '=', new_code)
            ])
            if not existing:
                return new_code
        
        # Fallback jika tidak bisa generate
        return f"{preferred_code}_DEP"
    
    # Create journal entry for deposit
    def _create_journal_entry(self):
        AccountMove = self.env['account.move']
        
        # Get or create deposit account based on type
        if self.type == 'receive':
            # Customer deposit (liability account)
            deposit_account = self._get_or_create_deposit_account('customer')
            counterpart_account = self.journal_id.default_account_id
            if not counterpart_account:
                raise UserError(_('Please configure default account for journal %s.') % self.journal_id.name)
        else:
            # Vendor deposit (asset account)  
            deposit_account = self._get_or_create_deposit_account('vendor')
            counterpart_account = self.journal_id.default_account_id
            if not counterpart_account:
                raise UserError(_('Please configure default account for journal %s.') % self.journal_id.name)
        
        move_vals = {
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'date': self.date,
            'company_id': self.company_id.id,
            'line_ids': [] # isi journal lines
        }
        
        # Create move deposit lines -> journal items
        if self.type == 'receive':
            # Debit: Bank/Cash, Credit: Customer Deposit
            line_vals = [
                {
                    'name': f'Deposit from {self.partner_id.name}',
                    'account_id': counterpart_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.amount_company_currency,
                    'credit': 0.0,
                },
                {
                    'name': f'Deposit from {self.partner_id.name}',
                    'account_id': deposit_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': self.amount_company_currency,
                }
            ]
            
            # Add currency info only if different from company currency [foreign currency]
            if self.currency_id != self.company_currency_id: 
                line_vals[0].update({
                    'currency_id': self.currency_id.id,
                    'amount_currency': self.amount, # Original foreign amount
                })
                line_vals[1].update({
                    'currency_id': self.currency_id.id,
                    'amount_currency': -self.amount, # Negative for credit
                })
            
            move_vals['line_ids'] = [(0, 0, line_vals[0]), (0, 0, line_vals[1])]
            
        else:
            # Debit: Vendor Deposit, Credit: Bank/Cash
            line_vals = [
                {
                    'name': f'Deposit to {self.partner_id.name}',
                    'account_id': deposit_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.amount_company_currency,
                    'credit': 0.0,
                },
                {
                    'name': f'Deposit to {self.partner_id.name}',
                    'account_id': counterpart_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': self.amount_company_currency,
                }
            ]
            
            # Add currency info only if different from company currency
            if self.currency_id != self.company_currency_id:
                line_vals[0].update({
                    'currency_id': self.currency_id.id,
                    'amount_currency': self.amount,
                })
                line_vals[1].update({
                    'currency_id': self.currency_id.id,
                    'amount_currency': -self.amount,
                })
            
            move_vals['line_ids'] = [(0, 0, line_vals[0]), (0, 0, line_vals[1])]
        
        move = AccountMove.create(move_vals)
        move.action_post()
        self.move_id = move.id


class ThinqDepositLine(models.Model):
    _name = 'thinq.deposit.line'
    _description = 'Thinq Deposit Usage Line'
    
    deposit_id = fields.Many2one(
        'thinq.deposit',
        string='Deposit',
        required=True,
        ondelete='cascade'
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Invoice/Bill',
        required=True
    )
    
    amount = fields.Monetary(
        string='Amount Used',
        currency_field='currency_id',
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='deposit_id.currency_id'
    )
    
    date = fields.Date(
        string='Usage Date',
        default=fields.Date.context_today
    )
    
    notes = fields.Char(string='Notes')