from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError

class StockPickingScrapLine(models.TransientModel):
    _inherit = "wiz.stock.picking.scrap.line"

    move_id = fields.Many2one('stock.move', 'Move', related='move_line_id.move_id', store=True)
    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Line', related='move_id.purchase_line_id', store=True)

    @api.constrains('quantity', 'purchase_line_id', 'move_id')
    def _constrains_qty(self):
        for rec in self:
            error = False
            if rec.purchase_line_id:
                if rec.purchase_line_id.product_qty < (rec.quantity + rec.purchase_line_id.scrapped_qty):
                    error = True
            else:
                if rec.move_id.product_uom_qty < rec.quantity:
                    error = True 
            if error:
                raise ValidationError(_(f'Quantity to Scrap [{rec.quantity + (rec.purchase_line_id.scrapped_qty or 0)}] cannot greater than Quantity Order/Demand [{rec.purchase_line_id.product_qty or rec.move_id.product_uom_qty}]'))

class StockPickingScrap(models.TransientModel):
    _inherit = 'wiz.stock.picking.scrap'

    picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type', required=True)
    barcode = fields.Char('Scan Barcode')

    @api.onchange('barcode')
    def _onchange_barcode(self):
        if not self.barcode:
            return
        product = self.env['product.product'].search([('barcode', '=', self.barcode)], limit=1)
        if product:
            for line in self.line_ids.filtered(lambda x:x.product_id.id == product.id):
                line.quantity += 1
        self.barcode = False

    def _prepare_picking(self, moves):
        vals = {
            'location_id': self.picking_type_id.default_location_src_id.id,
            'location_dest_id': self.picking_type_id.default_location_dest_id.id,
            'picking_type_id': self.picking_type_id.id,
            'scheduled_date': datetime.today(),
            'move_ids_without_package': moves
        }
        return vals

    def _prepare_move(self):
        vals = []
        for line in self.line_ids.filtered(lambda x:x.quantity > 0):
            po_line_id = False
            product_uom_id = line.uom_id.id if line.uom_id else line.product_id.uom_id.id
            if self.picking_id.purchase_id:
                po_line = self.picking_id.purchase_id.order_line.filtered(
                    lambda l: l.product_id == line.product_id
                )
                if po_line:
                    po_line_id = po_line[0].id
            vals.append((0, 0, {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom': product_uom_id,  # pastikan selalu terisi
                'product_uom_qty': line.quantity,
                'purchase_line_id': po_line_id,
            }))
        return vals

    def create_intermediate_scrap(self):
        if all(line.quantity <= 0 for line in self.line_ids):
            raise ValidationError(_('Please insert quantity to scrap! Cannot be empty!'))
        transfer_id = self.env['stock.picking'].create(self._prepare_picking(self._prepare_move()))
        transfer_id.action_confirm()
        transfer_id.action_assign()
        transfer_id.button_validate() 
        self.picking_id.message_post(body=_("Scrap has been created on: %s", transfer_id._get_html_link()))