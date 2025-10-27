from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
import re

_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_code = fields.Char('POS Code', required=True, help="Unique code for this POS, e.g. KCMT-123")

    street = fields.Char('Street')
    street2 = fields.Char('Street 2')
    city_id = fields.Many2one('res.city', string='City')
    state_id = fields.Many2one('res.country.state', 'State')
    zip = fields.Char('ZIP')
    country_id = fields.Many2one(
        'res.country', 'Country',
        default=lambda self: self._get_default_country()
    )
    phone = fields.Char('Phone')

    def _get_default_country(self):
        """Set default country to Indonesia"""
        indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
        return indonesia.id if indonesia else False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'country_id' in fields_list and not res.get('country_id'):
            indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
            if indonesia:
                res['country_id'] = indonesia.id
        return res

    # Sinkronisasi dengan city_id (sama seperti res.partner)
    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            # Auto-fill state_id dan country_id dari city
            if self.city_id.state_id:
                self.state_id = self.city_id.state_id
                if self.city_id.country_id:
                    self.country_id = self.city_id.country_id
            else:
                # Jika city ga punya state, kosongkan state tapi tetap Indonesia
                self.state_id = False
                if not self.country_id:
                    indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
                    if indonesia:
                        self.country_id = indonesia
        else:
            # Clear state, tapi tetap pertahankan Indonesia sebagai default country
            self.state_id = False
            if not self.country_id:
                indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
                if indonesia:
                    self.country_id = indonesia

    def _format_strip_phone(self, phone):
        """
        Format nomor menjadi +62XXXXXXXXXXX (tanpa strip).
        Input: +62 866-9999-955 → Output: +62866999955
        """
        # Pastikan awalan +62
        if not phone.startswith('+62'):
            return phone  # if format sdh +62

        # ambil digit setelah +62
        digits = re.sub(r'\D', '', phone[3:])  # ambil hanya angka setelah +62
        
        return '+62' + digits

    def _auto_format_phone_indonesia(self, phone):
        """Auto format phone number untuk Indonesia.
        Jika input tanpa awalan + atau 62, otomatis jadi +62 di depan.
        Format akhir: +62XXXXXXXXXXX (tanpa strip).
        """
        if not phone:
            return phone

        # hilangkan spasi dan strip dulu
        phone = phone.strip().replace(' ', '').replace('-', '')

        # Jika sudah +62 di depan, format tanpa strip
        if phone.startswith('+62'):
            formatted = self._format_strip_phone(phone)
            return formatted

        # Jika sudah 62 di depan (tanpa +), tambahkan +
        if phone.startswith('62'):
            phone = '+62' + phone[2:]
            formatted = self._format_strip_phone(phone)
            return formatted

        # Jika sudah + di depan (bukan +62), tetap ganti jadi +62
        if phone.startswith('+') and not phone.startswith('+62'):
            phone_wo_plus = phone[1:]
            phone = '+62' + phone_wo_plus.lstrip('0')
            formatted = self._format_strip_phone(phone)
            return formatted

        # Jika input hanya angka (tanpa awalan), tambahkan +62
        if re.match(r'^\d+$', phone):
            phone = '+62' + phone.lstrip('0')
            formatted = self._format_strip_phone(phone)
            return formatted

        # Jika input dimulai dengan 0, ganti jadi +62
        if phone.startswith('0'):
            phone = '+62' + phone[1:]
            formatted = self._format_strip_phone(phone)
            return formatted

        return phone

    @api.onchange('phone')
    def _onchange_phone(self):
        """Auto format phone ketika user input"""
        if self.phone:
            formatted_phone = self._auto_format_phone_indonesia(self.phone)
            if formatted_phone != self.phone:
                self.phone = formatted_phone

    @api.model_create_multi
    def create(self, vals_list):
        """Override create untuk auto-format phone dan set default country"""
        for vals in vals_list:
            # Auto-format phone numbers
            if 'phone' in vals and vals['phone']:
                vals['phone'] = self._auto_format_phone_indonesia(vals['phone'])
            
            # Set default country ke Indonesia jika belum ada
            if 'country_id' not in vals or not vals.get('country_id'):
                indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
                if indonesia:
                    vals['country_id'] = indonesia.id
                    
        return super().create(vals_list)

    def write(self, vals):
        """Override write untuk auto-format phone"""
        if 'phone' in vals and vals['phone']:
            vals['phone'] = self._auto_format_phone_indonesia(vals['phone'])
        return super().write(vals)

    @api.constrains('phone')
    def _check_unique_phone(self):
        """Validasi unique phone dan format"""
        def count_digits(s):
            return len(re.findall(r'\d', s))

        def clean_phone_number(s):
            """Auto-correct: hapus whitespace di sekitar tanda -"""
            cleaned = re.sub(r'\s*-\s*', '-', s)
            return cleaned.strip()

        phone_pattern = re.compile(r'^[\+\d\-\(\)\s]+$')

        def plus_sign_valid(s):
            """Hanya boleh ada satu + dan harus di awal (jika ada)."""
            plus_count = s.count('+')
            if plus_count == 0:
                return True
            if plus_count == 1 and s.strip().startswith('+'):
                return True
            return False

        def dash_valid(s):
            """Tidak boleh ada - di awal/akhir, tidak boleh --, dan tidak boleh - tanpa angka di kiri/kanan."""
            if s.startswith('-') or s.endswith('-'):
                return False
            if '--' in s:
                return False
            for i, c in enumerate(s):
                if c == '-':
                    if i == 0 or i == len(s) - 1:
                        return False
                    if not (s[i-1].isdigit() and s[i+1].isdigit()):
                        return False
            return True

        for record in self:
            if record.phone:
                phone = clean_phone_number(record.phone)
                
                if not phone_pattern.match(phone):
                    raise ValidationError(_('Phone number may only contain numbers, spaces, "+", "(", ")", and "-". Invalid format: "%s"') % record.phone)
                if not plus_sign_valid(phone):
                    raise ValidationError(_('Phone number: "+" sign is only allowed at the beginning. Invalid format: "%s"') % record.phone)
                if not dash_valid(phone):
                    raise ValidationError(_('Phone number: "-" is only allowed between digits and not at the start/end or doubled. Invalid format: "%s"') % record.phone)
                if count_digits(phone) < 8:
                    raise ValidationError(_('Phone number must contain at least 8 digits.'))
            
                # Cek duplicate dengan POS config lain
                existing_pos_phone = self.search([
                    ('phone', '=', record.phone),
                    ('id', '!=', record.id)
                ])
                if existing_pos_phone:
                    pos_name = existing_pos_phone[0].name or 'Unknown POS'
                    raise ValidationError(_('Phone number "%s" is already used by POS "%s".') % (record.phone, pos_name))
                
                # Cek duplicate dengan res.partner
                existing_partner_phone = self.env['res.partner'].search([
                    ('phone', '=', record.phone)
                ])
                if existing_partner_phone:
                    partner_name = existing_partner_phone[0].name or 'Unknown Partner'
                    raise ValidationError(_('Phone number "%s" is already used by partner "%s".') % (record.phone, partner_name))
                
                # Cek duplicate dengan hr.employee work_phone
                existing_employee_phone = self.env['hr.employee'].search([
                    ('work_phone', '=', record.phone)
                ])
                if existing_employee_phone:
                    employee_name = existing_employee_phone[0].name or 'Unknown Employee'
                    raise ValidationError(_('Phone number "%s" is already used by employee "%s".') % (record.phone, employee_name))

    def format_currency(self, amount, currency=None):
        """Format amount sesuai currency Odoo (IDR/others)"""
        try:
            if not currency:
                currency = self.env.company.currency_id
                
            symbol = currency.symbol or ''
            currency_name = currency.name or ''
            
            # Untuk IDR/Rupiah, gunakan format Indonesia
            if currency_name in ['IDR'] or symbol in ['Rp', 'IDR']:
                # Format Indonesia: Rp. 1.000,00
                # 1000000.50 -> 1,000,000.50 -> 1.000.000,50 -> Rp. 1.000.000,50
                formatted_number = f"{amount:,.2f}"  # 1,000,000.50
                formatted_number = formatted_number.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
                formatted = f"Rp. {formatted_number}"
            else:
                # Format internasional: $ 1,000.00
                formatted = f"{symbol} {amount:,.2f}"
            return formatted
        except Exception:
            return f"{symbol} {amount}"

    def use_coupon_code(self, *args, **kwargs):
        """Override to add validation before applying coupon"""
        code = args[0] if len(args) > 0 else kwargs.get('code')
        
        loyalty_card = self.env['loyalty.card'].search([('code', '=', code)], limit=1)
        if not loyalty_card:
            raise UserError('Invalid coupon code')
        
        program = loyalty_card.program_id

        today = fields.Date.context_today(self)
        if program.date_to and program.date_to < today:
            error_message = f"Coupon cannot be applied:\nPromo expired (End date: {program.date_to})"
            raise UserError(error_message)

        points_display_value = 0
        if loyalty_card.points_display:
            try:
                import re
                numbers = re.findall(r'\d+', loyalty_card.points_display)
                if numbers:
                    points_display_value = float(numbers[0])
                else:
                    points_display_value = 0
            except (ValueError, TypeError):
                points_display_value = 0

        if points_display_value <= 0:
            error_message = "Coupon cannot be applied:\nPromo sudah pernah digunakan"
            raise UserError(error_message)
        
        conditional_rules = program.rule_ids.filtered(lambda r: r.minimum_qty > 0 or r.minimum_amount > 0)
        
        if conditional_rules:
            rule = conditional_rules[0]
            
            total_qty, total_amount = self._get_current_order_totals()
            
            validation_errors = []
            
            if rule.minimum_qty and total_qty < rule.minimum_qty:
                validation_errors.append(f"Minimum {rule.minimum_qty} items required. Current: {int(total_qty)}")

            if rule.minimum_amount and total_amount < rule.minimum_amount:
                currency = self.currency_id or self.env.company.currency_id
                validation_errors.append(
                    f"Minimum purchase {self.format_currency(rule.minimum_amount, currency)} required. Current: {self.format_currency(total_amount, currency)}"
                )

            if validation_errors:
                error_message = 'Coupon cannot be applied:\n' + '\n'.join(validation_errors)
                raise UserError(error_message)

        result = super().use_coupon_code(*args, **kwargs)
        
        if isinstance(result, dict):
            result['program_date_to'] = program.date_to and program.date_to.strftime('%Y-%m-%d') or None
        
        return result
    
    def _get_current_order_totals(self):
        """Ambil total_qty dan amount_total dari context frontend"""
        total_qty = 0
        total_amount = 0

        try:
            context = self.env.context
            if 'amount_total' in context and 'total_qty' in context:
                total_qty = context['total_qty']
                total_amount = context['amount_total']
                return total_qty, total_amount

            if 'order_totals' in context:
                order_totals = context['order_totals']
                total_qty = order_totals.get('qty', 0)
                total_amount = order_totals.get('amount', 0)
                return total_qty, total_amount

        except Exception as e:
            _logger.error(f"Error extracting order totals: {e}")

        return total_qty, total_amount

    # nama POS gabole sama
    @api.constrains('name')
    def _check_unique_pos_name(self):
        for rec in self:
            if not rec.name:
                continue
            name_norm = rec.name.strip().casefold()
            candidates = self.with_context(force_company=False).search([('name', 'ilike', rec.name)])
            for c in candidates:
                if c.id == rec.id:
                    continue
                if c.name and c.name.strip().casefold() == name_norm:
                    raise ValidationError(_("POS Name '%s' is already used in another POS configuration (any company). Please use a unique name.") % rec.name)

    # kode POS gabole sama
    @api.constrains('pos_code')
    def _check_unique_pos_code(self):
        for rec in self:
            if not rec.pos_code:
                continue
            code_norm = rec.pos_code.strip().casefold()
            candidates = self.with_context(force_company=False).search([('pos_code', 'ilike', rec.pos_code)])
            for c in candidates:
                if c.id == rec.id:
                    continue
                if c.pos_code and c.pos_code.strip().casefold() == code_norm:
                    raise ValidationError(_("POS Code '%s' is already used in another POS configuration (any company). Please use a unique code.") % rec.pos_code)