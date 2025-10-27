from odoo import models, fields, _

class FrameShape(models.Model):
    _name = 'thinq.frame.shape'
    _description = 'Frame Shape Master'
    _rec_name = 'frame_shape_name'
    
    frame_shape_name = fields.Char(
        string='Frame Shape Name',
        required=True,
        help='Nama bentuk frame'
    )