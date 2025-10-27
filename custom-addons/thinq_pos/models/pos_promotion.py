from odoo import api, fields, models

class PosPromotionClass(models.Model):
    _name = "pos.promotion.class"
    _description = "Promotion Class"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
