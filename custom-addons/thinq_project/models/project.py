from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import re

class ProjectTask(models.Model):
    _inherit = 'project.task'

    customer_phone = fields.Char('Phone',)
    customer_email = fields.Char('Customer Email')
    customer_city_id = fields.Many2one('res.city',string='Customer City')
    last_contact_date = fields.Date('Last Contact Date')
    no_contact_attempts = fields.Integer('No of Contact Attempts')
    contact_result_id = fields.Many2one('thinq.project.contact.result', string='Contact Result')
    planned_visit = fields.Date('Planned Visit')
    visit_status_id = fields.Many2one('thinq.project.visit.status', string='Visit Status')

    _sql_constraints = [
        ('unique_customer_phone', 'unique(customer_phone)', 'Customer phone must be unique!'),
    ]
    
    def _sanitize_phone(self, phone):
        phone = re.sub(r'\D', '', phone)
        if phone.startswith('62'):
            phone = '0' + phone[2:]
        
        return phone
    
    @api.constrains('customer_phone')
    def _check_customer_phone_format(self):
        for rec in self:
            customer_phone = rec.customer_phone or ''
            if not (customer_phone.startswith('+62') or customer_phone.startswith('0')):
                raise ValidationError("The phone number must start with +62 or 0.")

    @api.constrains('customer_email')
    def _check_valid_email(self):
        for rec in self:
            if rec.customer_email:
                regex = r'^\S+@\S+\.\S+$'
                if not re.match(regex, rec.customer_email):
                    raise ValidationError(_("Invalid email format for %s") % rec.customer_email)

    @api.onchange('customer_phone')
    def _clean_phone(self):
        if self.customer_phone:
            self.customer_phone = self._sanitize_phone(self.customer_phone)

