from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPickingLabelLayout(models.TransientModel):
    _name = 'stock.picking.label.layout'
    _description = 'Stock Picking Product Label Layout'
    
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True)
    product_ids = fields.Many2many('product.product', string='Products to Print')
    
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get('active_id'):
            picking = self.env['stock.picking'].browse(self.env.context['active_id'])
            res['picking_id'] = picking.id
            # Get unique products from move lines
            products = picking.move_ids.mapped('product_id')
            res['product_ids'] = [(6, 0, products.ids)]
        return res
    
    def action_print_labels(self):
        """Print labels for selected products"""
        if not self.product_ids:
            raise UserError(_("Please select at least one product to print labels."))
        
        # Prepare data for printing
        products_data = []
        for product in self.product_ids:
            # Find total quantity for this product in the picking
            total_qty = sum(self.picking_id.move_ids.filtered(
                lambda m: m.product_id.id == product.id
            ).mapped('product_uom_qty'))
            
            # Tentukan quantity berdasarkan jenis picking
            if self.picking_id.picking_type_code == 'incoming':
                # Good Receipt (incoming) - print 1 label per product
                print_qty = 1
            else:
                # Delivery atau internal - print sesuai quantity
                print_qty = int(total_qty) if total_qty > 0 else 1
            
            products_data.append({
                'product_id': product.id,
                'product_name': product.name,
                'custom_quantity': print_qty,
            })
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'thinq_inventory.report_picking_product_label_custom',
            'report_type': 'qweb-pdf',
            'context': dict(
                self.env.context, 
                products_data=products_data,
                picking_id=self.picking_id.id
            ),
        }