from odoo import models, fields, api, _

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    customer_city_id = fields.Many2one(
        'res.city',
        string='Customer City',
        help='Kota tempat calon customer. Berhubungan dengan Module Contact.'
    )

    city_id = fields.Many2one(
        'res.city',
        string='City',
        help='City untuk address di Extra Information.'
    )

    # Override field city dengan computed (sync dengan city_id, bukan customer_city_id)
    city = fields.Char(
        string='City',
        compute='_compute_city_from_city_id',
        store=True,
        readonly=False
    )

    @api.depends('city_id')
    def _compute_city_from_city_id(self):
        """Compute city dari city_id (untuk address di Extra Information)"""
        for record in self:
            if record.city_id:
                record.city = record.city_id.name
            else:
                record.city = False
    
    @api.onchange('city_id')
    def _onchange_city_id(self):
        """Auto-fill state dan country dari city_id (untuk address)"""
        if self.city_id:
            if self.city_id.state_id:
                self.state_id = self.city_id.state_id
                if self.city_id.country_id:
                    self.country_id = self.city_id.country_id
            else:
                self.state_id = False
                self.country_id = False
        else:
            self.state_id = False
            self.country_id = False
    
    @api.onchange('partner_id')
    def _onchange_partner_id_city(self):
        """Auto-fill city dari contact yang dipilih"""
        if self.partner_id:
            # Sync city_id dari contact untuk address
            if hasattr(self.partner_id, 'city_id') and self.partner_id.city_id:
                self.city_id = self.partner_id.city_id
                # Optional: juga set customer_city_id
                self.customer_city_id = self.partner_id.city_id
            elif self.partner_id.city:
                city = self.env['res.city'].search([
                    ('name', 'ilike', self.partner_id.city)
                ], limit=1)
                if city:
                    self.city_id = city
                    self.customer_city_id = city
        else:
            self.city_id = False
            self.customer_city_id = False
