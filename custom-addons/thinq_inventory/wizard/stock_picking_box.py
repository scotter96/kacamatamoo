from odoo import _, api, fields, models

class StockPickingBoxLine(models.TransientModel):
    _name = 'stock.picking.box.line'
    _description = 'Box Packing Selection Line'

    pick_box_id = fields.Many2one('stock.picking.box', string='Pick Box', ondelete='cascade')
    name = fields.Char('Box Code', required=True)
    move_ids = fields.Many2many('stock.move', string='Products', required=True)

class StockPickingBox(models.TransientModel):
    _name = 'stock.picking.box'
    _description = 'Box Packing Selection'

    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True)
    available_move_ids = fields.Many2many('stock.move', string='Available Moves')
    selectable_moves = fields.Many2many('stock.move', string='Can Be Select', compute='_selectable_moves')
    line_ids = fields.One2many('stock.picking.box.line', 'pick_box_id', string='Lines')

    @api.depends('available_move_ids','line_ids.move_ids')
    def _selectable_moves(self):
        for rec in self:
            rec.selectable_moves = rec.available_move_ids - rec.line_ids.move_ids

    def action_confirm(self):
        for line in self.line_ids:
            for move in line.move_ids:
                move.box_code = line.name