from odoo import _, api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        res = super(StockPicking, self)._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type, partner)
        for rec in res.filtered(lambda x:x.state not in ('cancel','done')):
           #FIXME: trigger negative stock validation, defaultnya odoo nge-catch ValidationError
           rec._action_done()
        return res