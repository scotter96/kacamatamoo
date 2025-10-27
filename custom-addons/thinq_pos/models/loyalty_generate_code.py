from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LoyaltyGenerateWizard(models.TransientModel):
    _inherit = 'loyalty.generate.wizard'

    # Field untuk format voucher code
    code_format = fields.Selection([
        ('random', 'Random'),
        ('predefined', 'Predefined')
    ], string='Format', default='random', required=True,
       help="Choose the format for generating voucher codes")
    
    # Field untuk prefix (hanya muncul jika predefined)
    code_prefix = fields.Char(
        string='Prefix',
        help="Prefix for the voucher code (e.g., KCMT)"
    )
    
    # Field untuk digit count (hanya muncul jika predefined)
    code_digits = fields.Integer(
        string='Digits',
        default=4,
        help="Number of digits for the sequential number (e.g., 4 for 0001)"
    )

    @api.constrains('code_prefix', 'code_digits')
    def _check_predefined_fields(self):
        for record in self:
            if record.code_format == 'predefined':
                if not record.code_prefix:
                    raise ValidationError(_("Prefix is required when using Predefined format."))
                if record.code_digits <= 0:
                    raise ValidationError(_("Digits must be greater than 0."))
                if len(record.code_prefix) > 10:
                    raise ValidationError(_("Prefix should not exceed 10 characters."))

    @api.onchange('code_format')
    def _onchange_code_format(self):
        """Reset predefined fields when switching to random format"""
        if self.code_format == 'random':
            self.code_prefix = False
            self.code_digits = 4

    def generate_coupons(self):
        """Override method to handle custom code generation"""
        if self.code_format == 'predefined' and self.program_id.program_type == 'coupons':
            # Generate predefined coupons and RETURN directly (don't call super)
            return self._generate_predefined_coupons()
            
        # Only call original method for random format
        return super().generate_coupons()

    def _generate_predefined_coupons(self):
        """Generate coupons with predefined format"""
        # Get existing codes to avoid duplicates
        existing_codes = self.env['loyalty.card'].search([
            ('program_id', '=', self.program_id.id)
        ]).mapped('code')

        # Generate sequential codes
        generated_codes = []
        counter = 1
        codes_to_generate = self.coupon_qty

        while len(generated_codes) < codes_to_generate:
            # Format: PREFIX + zero-padded number
            code = f"{self.code_prefix}{str(counter).zfill(self.code_digits)}"
            
            # Check if code already exists
            if code not in existing_codes and code not in generated_codes:
                generated_codes.append(code)
            
            counter += 1
            
            # Safety check to prevent infinite loop
            if counter > 999999:
                raise ValidationError(_("Unable to generate enough unique codes. Please adjust your prefix or digits."))

        # Create loyalty cards with predefined codes directly
        loyalty_cards_vals = []
        for code in generated_codes:
            card_vals = {
                'program_id': self.program_id.id,
                'partner_id': self.mode == 'selected' and self.partner_id.id or False,
                'code': code,
                'points': self.points_granted or 0.0,
            }
            loyalty_cards_vals.append(card_vals)

        # Create all loyalty cards at once
        created_cards = self.env['loyalty.card'].create(loyalty_cards_vals)

        # Create history records for each card
        for card in created_cards:
            history_vals = {
                'card_id': card.id,
                'description': self.description or 'Generated coupon',
                'issued': self.points_granted or 0.0,
                'used': 0.0,
                'create_date': fields.Datetime.now(),
            }
            self.env['loyalty.history'].create(history_vals)
            
        # Return proper action to show generated coupons (like original method)
        try:
            action = self.env.ref('loyalty.loyalty_card_action').read()[0]
            action.update({
                'domain': [('id', 'in', created_cards.ids)],
                'context': {'create': False},
            })
            return action
        except:
            # Fallback: just close the wizard if action not found
            return {'type': 'ir.actions.act_window_close'}