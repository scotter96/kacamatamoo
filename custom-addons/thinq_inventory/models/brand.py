from odoo import models, fields, _

class Brand(models.Model):
    _name = 'thinq.brand'
    _description = 'Brand Master'
    _rec_name = 'brand_name'
    
    brand_name = fields.Char(
        string='Brand Name',
        required=True,
        help='Nama brand/merk'
    )