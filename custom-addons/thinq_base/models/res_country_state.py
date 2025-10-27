from odoo import _, api, fields, models

class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    city_ids = fields.One2many('res.city', 'state_id', string='Cities')