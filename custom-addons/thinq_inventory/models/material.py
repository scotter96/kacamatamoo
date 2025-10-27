from odoo import models, fields, _

class Material(models.Model):
    _name = 'thinq.material'
    _description = 'Material Master'
    _rec_name = 'material_name'
    
    material_name = fields.Char(
        string='Material Name',
        required=True,
        help='Nama material'
    )

