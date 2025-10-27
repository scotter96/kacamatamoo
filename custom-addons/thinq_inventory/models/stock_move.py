from odoo import _, api, fields, models

class StockMove(models.Model):
    _inherit = 'stock.move'

    box_code = fields.Char('Box Code')

    @api.depends('picking_id', 'product_id', 'location_id', 'location_dest_id')
    def _compute_display_name(self):
        for move in self:
            move.display_name = '%s%s' % (
                move.product_id.name,
                move.picking_id.origin and ' (%s)' % move.picking_id.origin or '')