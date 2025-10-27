from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def action_scrap_from_return(self):
        """Open Scrap form pre-filled with the picking being returned"""
        picking_id = self.picking_id.id
        if not picking_id:
            raise UserError(_("No picking found for this return."))

        picking = self.env['stock.picking'].browse(picking_id)

        # Pastikan picking sudah done untuk scrap
        if picking.state != 'done':
            raise UserError(_("You can only scrap products from validated pickings."))

        # Validasi bahwa ini adalah return document atau akan menjadi return document
        # (Scrap langsung dari wizard return sebelum return document dibuat)
        
        # Buat context default untuk stock.scrap
        context = {
            'default_picking_id': picking.id,
            'default_product_id': False,  # user pilih sendiri dari produk yang ada di picking
            'default_scrap_qty': 0.0,
            'from_return_wizard': True,  # flag bahwa ini dari return wizard
        }

        return {
            'name': _('Scrap Products from Return'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.scrap',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }
    
    def _validate_return_quantities(self):
        """Validasi quantity return sebelum create returns/exchanges"""
        for line in self.product_return_moves:
            # Hitung remaining quantity yang bisa di-return
            remaining_qty = line._get_remaining_returnable_quantity()
            
            if line.quantity > remaining_qty:
                original_qty = line.move_id.product_uom_qty
                already_returned = original_qty - remaining_qty
                
                raise ValidationError(_(
                    "Cannot proceed with return/exchange.\n\n"
                    "Return quantity (%.2f) exceeds available quantity for product '%s'.\n\n"
                    "Original received: %.2f\n"
                    "Already returned: %.2f\n"
                    "Available for return: %.2f\n\n"
                    "Please adjust the return quantities before proceeding."
                ) % (
                    line.quantity,
                    line.product_id.display_name,
                    original_qty,
                    already_returned,
                    remaining_qty
                ))
    
    def action_create_returns(self):
        """Override untuk validasi sebelum create returns"""
        # Validasi quantity sebelum membuat return
        self._validate_return_quantities()
        
        # Jika validasi lolos, lanjut ke method parent
        return super().action_create_returns()
    
    def action_create_exchanges(self):
        """Override untuk validasi sebelum create exchanges"""
        # Validasi quantity sebelum membuat exchange
        self._validate_return_quantities()
        
        # Jika validasi lolos, lanjut ke method parent
        return super().action_create_exchanges()

class StockReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    def _get_remaining_returnable_quantity(self):
        """Hitung sisa quantity yang bisa di-return untuk product ini"""
        self.ensure_one()
        
        # Quantity asli yang diterima
        original_qty = self.move_id.product_uom_qty
        
        # Cari semua return pickings yang sudah dibuat dari picking asli ini
        original_picking = self.wizard_id.picking_id
        
        # Cari return pickings yang terkait dengan picking asli
        # Return pickings biasanya memiliki origin yang mengandung nama picking asli
        return_pickings = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),  # Hanya yang sudah validated
            ('origin', 'ilike', original_picking.name)
        ])
        
        # Hitung total quantity yang sudah di-return untuk product ini
        total_returned = 0.0
        for return_pick in return_pickings:
            for move in return_pick.move_ids:
                if move.product_id == self.product_id:
                    total_returned += move.product_uom_qty
        
        # Sisa quantity yang bisa di-return
        remaining_qty = original_qty - total_returned
        
        return max(0.0, remaining_qty)  # Pastikan tidak negatif

    @api.constrains('quantity')
    def _check_return_quantity_limit(self):
        """Validasi real-time: Return quantity tidak boleh melebihi remaining returnable quantity"""
        for line in self:
            remaining_qty = line._get_remaining_returnable_quantity()
            
            if line.quantity > remaining_qty:
                original_qty = line.move_id.product_uom_qty
                already_returned = original_qty - remaining_qty
                
                raise ValidationError(_(
                    "Return quantity (%.2f) exceeds available quantity for product '%s'.\n\n"
                    "Original received: %.2f\n"
                    "Already returned: %.2f\n"
                    "Available for return: %.2f\n\n"
                    "Please adjust the return quantity."
                ) % (
                    line.quantity,
                    line.product_id.display_name,
                    original_qty,
                    already_returned,
                    remaining_qty
                ))

    @api.onchange('quantity')
    def _onchange_quantity_validation(self):
        """Validasi onchange untuk memberikan warning real-time saat user mengetik"""
        if self.quantity and self.move_id:
            remaining_qty = self._get_remaining_returnable_quantity()
            
            if self.quantity > remaining_qty:
                original_qty = self.move_id.product_uom_qty
                already_returned = original_qty - remaining_qty
                
                return {
                    'warning': {
                        'title': _('Invalid Return Quantity'),
                        'message': _(
                            "Return quantity (%.2f) exceeds available quantity for product '%s'.\n\n"
                            "Original received: %.2f\n"
                            "Already returned: %.2f\n"
                            "Available for return: %.2f\n\n"
                            "Please adjust the return quantity."
                        ) % (
                            self.quantity,
                            self.product_id.display_name,
                            original_qty,
                            already_returned,
                            remaining_qty
                        )
                    }
                }

    def write(self, vals):
        """Override write untuk validasi saat save manual"""
        result = super().write(vals)
        
        # Validasi setelah write jika quantity diubah
        if 'quantity' in vals:
            for line in self:
                remaining_qty = line._get_remaining_returnable_quantity()
                
                if line.quantity > remaining_qty:
                    original_qty = line.move_id.product_uom_qty
                    already_returned = original_qty - remaining_qty
                    
                    raise ValidationError(_(
                        "Return quantity (%.2f) exceeds available quantity for product '%s'.\n\n"
                        "Original received: %.2f\n"
                        "Already returned: %.2f\n"
                        "Available for return: %.2f\n\n"
                        "Please adjust the return quantity."
                    ) % (
                        line.quantity,
                        line.product_id.display_name,
                        original_qty,
                        already_returned,
                        remaining_qty
                    ))
        
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Override create untuk validasi saat create record baru"""
        results = super().create(vals_list)
        
        # Validasi setelah create untuk setiap record
        for result in results:
            remaining_qty = result._get_remaining_returnable_quantity()
            
            if result.quantity > remaining_qty:
                original_qty = result.move_id.product_uom_qty
                already_returned = original_qty - remaining_qty
                
                raise ValidationError(_(
                    "Return quantity (%.2f) exceeds available quantity for product '%s'.\n\n"
                    "Original received: %.2f\n"
                    "Already returned: %.2f\n"
                    "Available for return: %.2f\n\n"
                    "Please adjust the return quantity."
                ) % (
                    result.quantity,
                    result.product_id.display_name,
                    original_qty,
                    already_returned,
                    remaining_qty
                ))
        
        return results

