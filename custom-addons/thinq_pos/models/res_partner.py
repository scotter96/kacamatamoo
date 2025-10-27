import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    birthday = fields.Date('Birthday')
    ktp_file = fields.Binary(string="Upload KTP")

    created_today = fields.Boolean('Is Created Today', compute='_compute_created_today', store=False)

    # TODO: Temporary fixing
    total_all_due = fields.Float('Total All Due')
    total_all_overdue = fields.Float('Total All Due')
    has_moves = fields.Boolean('Has Moves')

    @api.depends('create_date')
    def _compute_created_today(self):
        today = fields.Date.today()
        for partner in self:
            if partner.create_date:
                partner.created_today = partner.create_date.date() == today and partner.is_customer_store
            else:
                partner.created_today = True

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += ['birthday', 'is_customer_store']
        return fields

    @api.model
    def set_as_customer(self, partner_id):
        partner = self.sudo().browse(partner_id)
        if partner:
            partner.write({
                    'is_customer_store': True
                })
            return True
        return False

    @api.model
    def open_customer_statement(self):
        # TODO: Temporary fixing
        pass

    def write(self, vals):
        """Override write to handle employee sync properly"""
        # Jika update berasal dari hr.employee, bypass beberapa validation
        if self.env.context.get('sync_from_employee'):
            return super(ResPartnerInherit, self).write(vals)
        
        # Jika bukan dari employee sync, lanjutkan dengan validasi normal
        return super(ResPartnerInherit, self).write(vals)

    @api.constrains('email')
    def _check_email_format(self):
        """Validasi format email harus xxx@domain.com"""
        for record in self:
            if record.email:
                # Pattern regex untuk validasi email
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                
                if not re.match(email_pattern, record.email.strip()):
                    raise ValidationError(
                        _('Email format is invalid. Please enter a valid email address like "example@domain.com".')
                    )
