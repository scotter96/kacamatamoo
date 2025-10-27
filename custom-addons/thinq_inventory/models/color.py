from odoo import models, fields, _

class Color(models.Model):
    _name = 'thinq.color'
    _description = 'Color Master'
    _rec_name = 'color_name'

    
    color_name = fields.Char(
        string='Color Name',
        required=True,
        help='Nama warna'
    )
    
    color_type = fields.Char(
        string='Color',
        help='Kode warna/color picker'
    )