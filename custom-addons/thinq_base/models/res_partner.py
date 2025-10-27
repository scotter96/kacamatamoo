import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Custom fields for partner classification
    is_customer_store = fields.Boolean(
        string="Is Customer Store",
        default=False,
        help="Penanda apabila contact merupakan Customer Store."
    )
    
    is_customer_b2b = fields.Boolean(
        string="Is Customer B2B", 
        default=False,
        help="Penanda apabila contact merupakan Customer B2B."
    )
    
    is_customer_marketplace = fields.Boolean(
        string="Is Customer Marketplace",
        default=False,
        help="Penanda apabila contact merupakan Customer Marketplace."
    )
    
    is_vendor = fields.Boolean(
        string="Is Vendor",
        default=False,
        help="Penanda apabila contact merupakan Vendor."
    )

    is_employee = fields.Boolean(
        string="Is Employee",
        default=False,
        help="Penanda apabila contact merupakan Employee.",
        compute='_compute_is_employee',
        store=True
    )

    # Tampilan UI sebagai City, dihubungkan ke model res.city
    city_id = fields.Many2one(
        'res.city',
        string='City',
    )

    # Override the original city field (res.partner) to sync with city_id
    city = fields.Char(
        string='City (Old)',
        compute='_compute_city_from_city_id',
        store=True,
        readonly=False
    )

    # Override country_id dengan default Indonesia
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        ondelete='restrict',
        default=lambda self: self._get_default_country()
    )

    # Multiple company selection field
    company_ids = fields.Many2many(
        'res.company',
        string='Companies',
        help='Companies associated with this partner'
    )

    def _get_default_country(self):
        """Set default country to Indonesia"""
        indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
        return indonesia.id if indonesia else False

    @api.model
    def default_get(self, fields_list):
        """Override default_get untuk memastikan Indonesia terpilih sebagai default country"""
        res = super().default_get(fields_list)
        if 'country_id' in fields_list and not res.get('country_id'):
            indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
            if indonesia:
                res['country_id'] = indonesia.id
        return res

    @api.depends('employee_ids')
    def _compute_is_employee(self):
        for rec in self:
            rec.is_employee = bool(rec.employee_ids)

    def _format_strip_phone(self, phone):
        """
        Format nomor menjadi +62XXXXXXXXXXX (tanpa strip).
        Input: +62 866-9999-955 → Output: +62866999955
        """
        # Pastikan awalan +62
        if not phone.startswith('+62'):
            return phone  # hanya format jika sudah +62

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

        # Default: kembalikan apa adanya
        return phone

    @api.onchange('phone')
    def _onchange_phone(self):
        """Auto format phone ketika user input"""
        if self.phone:
            formatted_phone = self._auto_format_phone_indonesia(self.phone)
            if formatted_phone != self.phone:
                self.phone = formatted_phone

    @api.onchange('mobile')
    def _onchange_mobile(self):
        """Auto format mobile ketika user input"""
        if self.mobile:
            formatted_mobile = self._auto_format_phone_indonesia(self.mobile)
            if formatted_mobile != self.mobile:
                self.mobile = formatted_mobile

    @api.model_create_multi
    def create(self, vals_list):
        """Override create untuk auto-format phone dan set default country sebelum constraint check"""
        for vals in vals_list:
            # Auto-format phone numbers
            if 'phone' in vals and vals['phone']:
                vals['phone'] = self._auto_format_phone_indonesia(vals['phone'])
            if 'mobile' in vals and vals['mobile']:
                vals['mobile'] = self._auto_format_phone_indonesia(vals['mobile'])
            
            # Set default country ke Indonesia jika belum ada
            if 'country_id' not in vals or not vals.get('country_id'):
                indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
                if indonesia:
                    vals['country_id'] = indonesia.id
                    
        return super().create(vals_list)

    def write(self, vals):
        """Override write untuk auto-format phone sebelum constraint check"""
        if 'phone' in vals and vals['phone']:
            vals['phone'] = self._auto_format_phone_indonesia(vals['phone'])
        if 'mobile' in vals and vals['mobile']:
            vals['mobile'] = self._auto_format_phone_indonesia(vals['mobile'])
        return super().write(vals)

    # Constraint untuk unique phone dan mobile
    @api.constrains('phone', 'mobile')
    def _check_unique_phone_mobile(self):
        """Validasi unique phone dan mobile dengan skip option dari context"""
        # Skip validasi jika context flag ada (untuk sync dari employee)
        if self.env.context.get('skip_phone_validation'):
            return
        
        # Skip jika sedang sync dari employee
        if self.env.context.get('sync_from_employee'):
            return
            
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
            # Tidak boleh ada - yang tidak diapit angka
            for i, c in enumerate(s):
                if c == '-':
                    if i == 0 or i == len(s) - 1:
                        return False
                    if not (s[i-1].isdigit() and s[i+1].isdigit()):
                        return False
            return True

        for record in self:
            if record.phone:
                # Auto-correct phone number tapi jgn assign kembali ke record
                phone = clean_phone_number(record.phone)
                
                if not phone_pattern.match(phone):
                    raise ValidationError(_('Phone number may only contain numbers, spaces, "+", "(", ")", and "-". Invalid format: "%s"') % record.phone)
                if not plus_sign_valid(phone):
                    raise ValidationError(_('Phone number: "+" sign is only allowed at the beginning. Invalid format: "%s"') % record.phone)
                if not dash_valid(phone):
                    raise ValidationError(_('Phone number: "-" is only allowed between digits and not at the start/end or doubled. Invalid format: "%s"') % record.phone)
                if count_digits(phone) < 8:
                    raise ValidationError(_('Phone number must contain at least 8 digits.'))
            
                # Cek duplicate tapi exclude partner yang sedang di-update
                existing_phone = self.search([
                    ('phone', '=', record.phone),
                    ('id', '!=', record.id)
                ])
                if existing_phone:
                    partner_name = existing_phone[0].name or 'Unknown Partner'
                    raise ValidationError(_('Phone number "%s" is already used by %s.') % (record.phone, partner_name))
                
                # Cek duplicate dengan hr.employee work_phone
                # Skip jika partner ini adalah related partner dari employee dengan nama yang sama
                existing_employee_phone = self.env['hr.employee'].search([
                    ('work_phone', '=', record.phone)
                ])
                if existing_employee_phone:
                    # Skip validasi jika nama partner sama dengan nama employee
                    if existing_employee_phone[0].name != record.name:
                        employee_name = existing_employee_phone[0].name or 'Unknown Employee'
                        raise ValidationError(_('Phone number "%s" is already used by employee %s.') % (record.phone, employee_name))

            if record.mobile:
                # Auto-correct mobile number tapi jgn assign kembali ke record
                mobile = clean_phone_number(record.mobile)
                
                if not phone_pattern.match(mobile):
                    raise ValidationError(_('Mobile number may only contain numbers, spaces, "+", "(", ")", and "-". Invalid format: "%s"') % record.mobile)
                if not plus_sign_valid(mobile):
                    raise ValidationError(_('Mobile number: "+" sign is only allowed at the beginning. Invalid format: "%s"') % record.mobile)
                if not dash_valid(mobile):
                    raise ValidationError(_('Mobile number: "-" is only allowed between digits and not at the start/end or doubled. Invalid format: "%s"') % record.mobile)
                if count_digits(mobile) < 8:
                    raise ValidationError(_('Mobile number must contain at least 8 digits.'))
                
                # Cek duplicate tapi exclude partner yang sedang di-update
                existing_mobile = self.search([
                    ('mobile', '=', record.mobile),
                    ('id', '!=', record.id)
                ])
                if existing_mobile:
                    partner_name = existing_mobile[0].name or 'Unknown Partner'
                    raise ValidationError(_('Mobile number "%s" is already used by %s.') % (record.mobile, partner_name))
                
                # Cek duplicate dengan hr.employee mobile_phone
                # Skip jika partner ini adalah related partner dari employee dengan nama yang sama
                existing_employee_mobile = self.env['hr.employee'].search([
                    ('mobile_phone', '=', record.mobile)
                ])
                if existing_employee_mobile:
                    # Skip validasi jika nama partner sama dengan nama employee
                    if existing_employee_mobile[0].name != record.name:
                        employee_name = existing_employee_mobile[0].name or 'Unknown Employee'
                        raise ValidationError(_('Mobile number "%s" is already used by employee %s.') % (record.mobile, employee_name))

    # Compute method to set city based on city_id
    @api.depends('city_id')
    def _compute_city_from_city_id(self):
        for record in self:
            if record.city_id:
                record.city = record.city_id.name
            elif not record.city_id and not record.city:
                record.city = False

    # Sinkronisasi antara city_id dan city
    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            # Set city name from city_id
            self.city = self.city_id.name
            
            # Auto-fill state_id dan country_id dari city
            if self.city_id.state_id:
                # Jika city memiliki state, auto-fill state dan country
                self.state_id = self.city_id.state_id
                if self.city_id.country_id:
                    self.country_id = self.city_id.country_id
            else:
                # Jika city tidak memiliki state, kosongkan state dan country
                self.state_id = False
                # Tetap set Indonesia sebagai default jika tidak ada country dari city
                if not self.country_id:
                    indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
                    if indonesia:
                        self.country_id = indonesia
        else:
            # Clear city dan state, tapi tetap pertahankan Indonesia sebagai default country
            self.city = False
            self.state_id = False
            if not self.country_id:
                indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
                if indonesia:
                    self.country_id = indonesia
            
    @api.onchange('city')
    def _onchange_city(self):
        if self.city and not self.city_id:
            # Try to find matching city
            city_obj = self.env['res.city'].search([
                ('name', '=ilike', self.city)
            ], limit=1)
            
            if city_obj:
                self.city_id = city_obj
                # Trigger city_id onchange to sync state and country
                self._onchange_city_id()

    @api.constrains('phone')
    def _check_phone_required(self):
        """Memastikan phone field wajib diisi"""
        for record in self:
            if not record.phone or not record.phone.strip():
                raise ValidationError(_('Phone number is required and cannot be empty.'))