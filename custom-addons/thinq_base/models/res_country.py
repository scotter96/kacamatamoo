from odoo import models, fields, api

class ResCountry(models.Model):
    _inherit = 'res.country'

    display_name = fields.Char(compute='_compute_display_name', store=False)

    @api.depends('name', 'phone_code')
    def _compute_display_name(self):
        for rec in self:
            if rec.phone_code:
                rec.display_name = f"{rec.name} (+{rec.phone_code})"
            else:
                rec.display_name = rec.name

    # gagal pakai ini kyknya di odoo base udh ada jd hrs pakai cara display_name (prior 1)
    # def name_get(self):
    #     result = []
    #     for rec in self:
    #         if rec.phone_code:
    #             name = f"{rec.name} +{rec.phone_code}"
    #         else:
    #             name = rec.name
    #         result.append((rec.id, name))
    #     return result