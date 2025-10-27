from odoo import models, fields, api
import secrets
import string

class UrlShortener(models.Model):
    _name = "url.shortener"
    _description = "URL Shortener"

    name = fields.Char("Short Code", required=True, index=True, copy=False)
    original_url = fields.Char("Original URL", required=True)
    click_count = fields.Integer("Clicks", default=0)

    _sql_constraints = [
        ('unique_short_code', 'unique(name)', 'Short code must be unique.')
    ]

    @api.model
    def generate_short_url(self, original_url):
        alphabet = string.ascii_letters + string.digits
        code = ''.join(secrets.choice(alphabet) for _ in range(6))
        record = self.create({
            'name': code,
            'original_url': original_url,
        })
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/s/{record.name}"
