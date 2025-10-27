from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    so_auto_no_backorder = fields.Boolean(
        string='Auto No Backorder for Sales Orders',
        config_parameter='thinq_inventory.so_auto_no_backorder',
        help='When enabled, delivery orders from sales orders will automatically select "No Backorder" '
             'when there is outstanding quantity (demand > delivered)'
    )
