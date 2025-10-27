from odoo import models, fields, api, _

class ThinqInventoryStockLocation(models.Model):
    """
    Additional field and function for stock.location
    """
    _inherit = 'stock.location'
    _description = 'Additional field and function for stock.location'
    
    is_missing_location = fields.Boolean(string="Location to Store Missing QTY")