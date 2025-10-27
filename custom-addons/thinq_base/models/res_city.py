from odoo import _, api, fields, models

class ResCity(models.Model):
    _name = "res.city"
    _description = "City"
    _order = "id, name asc"

    name = fields.Char(string="City Name", required=True)
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="State",
        ondelete="cascade",
    )
    country_id = fields.Many2one(
        related="state_id.country_id",
        string="Country",
        store=True,
        readonly=True,
    )