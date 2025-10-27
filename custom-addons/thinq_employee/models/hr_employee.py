from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging
import secrets

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Override work_phone untuk required
    work_phone = fields.Char(required=True, help="Work phone number is required")
    
    # Override private_country_id dengan default Indonesia
    private_country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self._get_default_country()
    )

    def generate_random_pin(self):
        digits = '123456789'
        existing_pins = set(self.search([]).mapped('pin'))
        pin = ''
        while not pin or pin in existing_pins:
            pin = ''.join(secrets.choice(digits) for _ in range(4))
        self.pin = pin

    def send_email_pin(self):
        template = self.env.ref('thinq_employee.mail_template_employee_pin')
        template.send_mail(self.id, force_send=True)

    def _get_default_country(self):
        """Set default country to Indonesia"""
        indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
        return indonesia.id if indonesia else False

    @api.model
    def default_get(self, fields_list):
        """Override default_get untuk memastikan Indonesia terpilih sebagai default country"""
        res = super().default_get(fields_list)
        if 'private_country_id' in fields_list and not res.get('private_country_id'):
            indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
            if indonesia:
                res['private_country_id'] = indonesia.id
        return res

    def _format_strip_phone(self, phone):
        """
        Format nomor menjadi +62XXXXXXXXXXX (tanpa strip).
        Input: +62 866-9999-955 → Output: +62866999955
        """
        # Pastikan awalan +62
        if not phone.startswith('+62'):
            return phone  # hanya format jika sudah +62

        # Ambil digit setelah +62 dan hilangkan semua karakter non-digit
        digits = re.sub(r'\D', '', phone[3:])  # ambil hanya angka setelah +62
        
        return '+62' + digits

    def _auto_format_phone_indonesia(self, phone):
        """Auto format phone number untuk Indonesia.
        Jika input tanpa awalan + atau 62, otomatis jadi +62 di depan.
        Format akhir: +62XXXXXXXXXXX (tanpa strip).
        """
        if not phone:
            return phone

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

    @api.onchange('work_phone')
    def _onchange_work_phone(self):
        """Auto format work_phone ketika user input"""
        if self.work_phone:
            formatted_phone = self._auto_format_phone_indonesia(self.work_phone)
            if formatted_phone != self.work_phone:
                self.work_phone = formatted_phone

    @api.onchange('mobile_phone')
    def _onchange_mobile_phone(self):
        """Auto format mobile_phone ketika user input"""
        if self.mobile_phone:
            formatted_mobile = self._auto_format_phone_indonesia(self.mobile_phone)
            if formatted_mobile != self.mobile_phone:
                self.mobile_phone = formatted_mobile

    @api.constrains('work_phone')
    def _check_work_phone_required(self):
        """Memastikan work_phone field wajib diisi"""
        for record in self:
            if not record.work_phone or not record.work_phone.strip():
                raise ValidationError(_('Work phone number is required and cannot be empty.'))

    def _normalize_phone(self, phone, country_code='+62'):
        """Normalisasi nomor telepon agar format berbeda tetap dianggap sama."""
        if not phone:
            return ''
        # Hilangkan semua karakter non-digit kecuali +
        phone = phone.strip()
        digits = re.sub(r'[^\d+]', '', phone)
        # Jika mulai dengan +, ambil setelah kode negara
        if digits.startswith('+'):
            digits = digits.lstrip('+')
            # Hilangkan kode negara jika ada
            if digits.startswith(country_code.lstrip('+')):
                digits = digits[len(country_code.lstrip('+')):]
        # Hilangkan leading zero
        digits = digits.lstrip('0')
        # Gabungkan dengan kode negara
        return country_code + digits

    def _check_unique_employee_phone_mobile(self, vals, exclude_ids=None):
        """Cek duplikat phone/mobile di res.partner dan hr.employee dengan normalisasi."""
        # Skip validasi jika ada context flag
        if self.env.context.get('skip_phone_validation'):
            return
            
        country_code = '+62'
        phone = vals.get('work_phone')
        mobile = vals.get('mobile_phone')
        employee_name = vals.get('name', '')

        normalized_phone = self._normalize_phone(phone, country_code) if phone else None
        normalized_mobile = self._normalize_phone(mobile, country_code) if mobile else None

        # Tentukan IDs yang harus di-exclude
        if exclude_ids is None:
            exclude_ids = []

        # Cek di res.partner (exclude partner yang terkait dengan employee yang di-exclude)
        if normalized_phone:
            # Dapatkan nama employee yang di-exclude untuk skip partner dengan nama yang sama
            excluded_names = []
            if exclude_ids:
                excluded_employees = self.env['hr.employee'].browse(exclude_ids)
                excluded_names = [emp.name for emp in excluded_employees if emp.name]
            
            # Jika sedang create dan ada nama, tambahkan ke excluded_names
            if employee_name:
                excluded_names.append(employee_name)
            
            partners = self.env['res.partner'].search([
                ('phone', '!=', False),
                ('name', 'not in', excluded_names)
            ])
            for partner in partners:
                if self._normalize_phone(partner.phone, country_code) == normalized_phone:
                    raise ValidationError(f'Nomor telepon "{phone}" sudah digunakan di contact "{partner.name}".')

        if normalized_mobile:
            # Dapatkan nama employee yang di-exclude
            excluded_names = []
            if exclude_ids:
                excluded_employees = self.env['hr.employee'].browse(exclude_ids)
                excluded_names = [emp.name for emp in excluded_employees if emp.name]
            
            # Jika sedang create dan ada nama, tambahkan ke excluded_names
            if employee_name:
                excluded_names.append(employee_name)
            
            partners = self.env['res.partner'].search([
                ('mobile', '!=', False),
                ('name', 'not in', excluded_names)
            ])
            for partner in partners:
                if self._normalize_phone(partner.mobile, country_code) == normalized_mobile:
                    raise ValidationError(f'Nomor mobile "{mobile}" sudah digunakan di contact "{partner.name}".')

        # Cek di hr.employee (exclude diri sendiri dan employee dengan nama yang sama)
        if normalized_phone:
            domain = [
                ('work_phone', '!=', False),
                ('id', 'not in', exclude_ids)
            ]
            # Jika sedang create dan ada nama, exclude employee dengan nama yang sama
            if employee_name:
                domain.append(('name', '!=', employee_name))
            
            employees = self.env['hr.employee'].search(domain)
            for employee in employees:
                if self._normalize_phone(employee.work_phone, country_code) == normalized_phone:
                    raise ValidationError(f'Nomor telepon "{phone}" sudah digunakan di employee "{employee.name}".')

        if normalized_mobile:
            domain = [
                ('mobile_phone', '!=', False),
                ('id', 'not in', exclude_ids)
            ]
            # Jika sedang create dan ada nama, exclude employee dengan nama yang sama
            if employee_name:
                domain.append(('name', '!=', employee_name))
            
            employees = self.env['hr.employee'].search(domain)
            for employee in employees:
                if self._normalize_phone(employee.mobile_phone, country_code) == normalized_mobile:
                    raise ValidationError(f'Nomor mobile "{mobile}" sudah digunakan di employee "{employee.name}".')

    def _find_related_partner(self):
        """Finds the related partner by matching the employee's name."""
        self.ensure_one()
        # cari nama partner dengan nama yang sama persis
        return self.env['res.partner'].search([('name', '=', self.name)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):    
        # Auto-format phone numbers dan set default country sebelum validation
        for vals in vals_list:
            if 'work_phone' in vals and vals['work_phone']:
                vals['work_phone'] = self._auto_format_phone_indonesia(vals['work_phone'])
            if 'mobile_phone' in vals and vals['mobile_phone']:
                vals['mobile_phone'] = self._auto_format_phone_indonesia(vals['mobile_phone'])
            
            # Set default country ke Indonesia jika belum ada
            if 'private_country_id' not in vals or not vals.get('private_country_id'):
                indonesia = self.env['res.country'].search([('code', '=', 'ID')], limit=1)
                if indonesia:
                    vals['private_country_id'] = indonesia.id
            
            # Validasi duplikat sebelum create
            self._check_unique_employee_phone_mobile(vals, exclude_ids=[])
            
        # Create employee dengan context khusus untuk skip validasi di partner
        employees = super(HrEmployee, self.with_context(skip_phone_validation=True)).create(vals_list)
        
        for employee, vals in zip(employees, vals_list):
            partner = employee._find_related_partner()
            # sync phone + birthday + country dengan partner di hr.employee
            if partner:
                partner_vals = {}
                if 'work_phone' in vals:
                    partner_vals['phone'] = vals['work_phone']
                if 'mobile_phone' in vals:
                    partner_vals['mobile'] = vals['mobile_phone']
                if 'birthday' in vals:
                    partner_vals['birthday'] = vals['birthday']
                if 'private_country_id' in vals:
                    partner_vals['country_id'] = vals['private_country_id']
                if partner_vals:
                    partner.with_context(
                        skip_employee_sync=True,
                        sync_from_employee=True,
                        skip_ktp_validation=True,
                        skip_phone_validation=True  # Skip validasi phone di partner
                    ).sudo().write(partner_vals)
        return employees

    def write(self, vals):
        # Auto-format phone numbers sebelum validation
        if 'work_phone' in vals and vals['work_phone']:
            vals['work_phone'] = self._auto_format_phone_indonesia(vals['work_phone'])
        if 'mobile_phone' in vals and vals['mobile_phone']:
            vals['mobile_phone'] = self._auto_format_phone_indonesia(vals['mobile_phone'])
        
        # Hanya lakukan validation jika ada perubahan phone/mobile
        if 'work_phone' in vals or 'mobile_phone' in vals:
            # Pass semua IDs yang sedang di-update untuk di-exclude dari pengecekan
            self._check_unique_employee_phone_mobile(vals, exclude_ids=self.ids)
    
        # Write dengan context untuk skip validasi di partner
        result = super(HrEmployee, self.with_context(skip_phone_validation=True)).write(vals)
        
        # Sync ke partner jika ada perubahan
        fields_to_sync = ['work_phone', 'mobile_phone', 'birthday', 'private_country_id']
        if any(field in vals for field in fields_to_sync):
            for employee in self:
                partner = employee._find_related_partner()
                
                if partner:
                    partner_vals = {}
                    
                    if 'work_phone' in vals:
                        partner_vals['phone'] = vals['work_phone']
                    
                    if 'mobile_phone' in vals:
                        partner_vals['mobile'] = vals['mobile_phone']

                    if 'birthday' in vals:
                        partner_vals['birthday'] = vals['birthday']
                    
                    if 'private_country_id' in vals:
                        partner_vals['country_id'] = vals['private_country_id']
                    
                    if partner_vals:
                        partner.with_context(
                            sync_from_employee=True,
                            skip_ktp_validation=True,
                            skip_phone_validation=True  # Skip validasi phone di partner
                        ).sudo().write(partner_vals)
        
        return result