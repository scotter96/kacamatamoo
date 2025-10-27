from odoo import api, models
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict

PICK_PACK_STATE = [('picking','Picking'),('packing','Packing')]

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_intermediate_scrap = fields.Boolean(string='Intermediate Scrap')

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    picking_or_packing = fields.Selection(PICK_PACK_STATE, default='picking', copy=False, tracking=True)

    def action_box(self):
        grouped_moves = defaultdict(list)
        for move in self.move_ids_without_package:
            if move.box_code:
                grouped_moves[move.box_code].append(move.id)
        lines = []

        for box_code, move_ids in grouped_moves.items():
            lines.append((0, 0, {
                'name': box_code,
                'move_ids': [(6, 0, move_ids)],
            }))

        action = self.env.ref('thinq_inventory.stock_picking_box_action').read()[0]
        action['context'] = {
            'default_picking_id': self.id,
            'default_available_move_ids': [(6,0,self.move_ids_without_package.ids)],
            'default_line_ids': lines
        }

        return action

    def set_packing(self):
        self.picking_or_packing = 'packing'
    
    def set_picking(self):
        self.picking_or_packing = 'picking'

    def action_print_shipping_label(self):
        return self.env.ref('thinq_inventory.shipping_label_report_action').with_context(
            discard_logo_check=True,
            force_report_rendering=True
        ).report_action(self)
        
    show_scrap_button = fields.Boolean(
        compute='_compute_show_scrap_button',
        store=False
    )

    def button_whole_scrap(self):
        res = super(StockPicking, self).button_whole_scrap()
        picking_type_id = self.env['stock.picking.type'].search([
            ('is_intermediate_scrap', '=', True),
            ('warehouse_id', '=', self.picking_type_id.warehouse_id.id),
        ],limit=1)
        if not picking_type_id:
            raise ValidationError(_('Intermediate Picking Type is not found. Please contact your Administrator!'))
        res['context'] = {'default_picking_id': self.id, 'default_picking_type_id': picking_type_id.id}
        return res

    @api.depends('state', 'picking_type_code', 'origin')
    def _compute_show_scrap_button(self):
        for rec in self:
            # Show untuk incoming yang sudah done
            if rec.state == 'done' and rec.picking_type_code == 'incoming':
                rec.show_scrap_button = True
            # Show untuk outgoing yang sudah done DAN merupakan return document
            elif (rec.state == 'done' and 
                  rec.picking_type_code == 'outgoing' and 
                  rec.origin and 'return' in rec.origin.lower()):
                rec.show_scrap_button = True
            else:
                rec.show_scrap_button = False

    
    def button_validate(self):
        """Override button_validate to handle validations and auto no-backorder"""
        
        # PRIORITY 1: Receipt quantity validation for incoming pickings
        if self.picking_type_code == 'incoming':
            self._check_receipt_qty_validation()
        
        # PRIORITY 2: Delivery quantity validation for outgoing pickings
        if self.picking_type_code == 'outgoing':
            self._check_delivery_qty_validation()
        
        # PRIORITY 3: Auto no-backorder logic for outgoing pickings
        auto_no_backorder = self.env['ir.config_parameter'].sudo().get_param(
            'thinq_inventory.so_auto_no_backorder', default='False'
        ).lower() in ('true', '1', 'yes')
        
        if (auto_no_backorder and 
            self.picking_type_code == 'outgoing' and 
            self.sale_id and 
            self._has_outstanding_qty()):
            
            # Adjust quantities to prevent backorder creation
            for move in self.move_ids:
                delivered_qty = sum(move.move_line_ids.mapped('quantity'))
                if move.product_uom_qty > delivered_qty:
                    move.write({'product_uom_qty': delivered_qty})
            
            # Setelah adjust, panggil super dengan context
            return super(StockPicking, self.with_context(cancel_backorder=True)).button_validate()
        
        return super().button_validate()
    
    def _action_done(self):
        """Override _action_done to handle validations"""
        
        # Validation for incoming pickings - receipt validation
        if self.picking_type_code == 'incoming':
            self._check_receipt_qty_validation()
        
        # Validation for outgoing pickings - delivery validation
        if self.picking_type_code == 'outgoing':
            self._check_delivery_qty_validation()
        
        return super()._action_done()
    
    def _has_outstanding_qty(self):
        """Check if delivery has outstanding quantity (demand > delivered)"""
        for move in self.move_ids:
            # Use move_line_ids to get actual delivered quantity
            delivered_qty = sum(move.move_line_ids.mapped('quantity'))
            if move.product_uom_qty > delivered_qty:
                return True
        return False
    
    
    def _check_receipt_qty_validation(self):
        """Check if receipt quantity does not exceed demand quantity"""
        for move in self.move_ids:
            # TOTAL per move (sum dari semua move lines untuk move ini)
            total_received = sum(move.move_line_ids.mapped('quantity'))
            if total_received > move.product_uom_qty:
                raise ValidationError(
                    _("Total receipt quantity (%.2f) cannot exceed demand quantity (%.2f) for product '%s'") % (
                        total_received,
                        move.product_uom_qty,
                        move.product_id.display_name
                    )
                )
            
    def _check_delivery_qty_validation(self):
        """Check if delivery quantity does not exceed demand quantity"""
        for move in self.move_ids:
            # TOTAL per move (sum dari semua move lines untuk move ini)
            total_delivered = sum(move.move_line_ids.mapped('quantity'))
            if total_delivered > move.product_uom_qty:
                raise ValidationError(
                    _("Total delivery quantity (%.2f) cannot exceed demand quantity (%.2f) for product '%s'") % (
                        total_delivered,
                        move.product_uom_qty,
                        move.product_id.display_name
                    )
                )
            
    def action_print_product_labels(self):
        """Open wizard to select products for label printing"""
        # Get unique products from move lines
        products = self.move_ids.mapped('product_id')
        
        if not products:
            raise UserError(_("No products found in this picking to print labels."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Product Labels'),
            'res_model': 'stock.picking.label.layout',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'available_products': products.ids,
            }
        }
        
class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    picking_id = fields.Many2one('stock.picking', string="Picking", readonly=True)
    
    # Override state untuk menambah state 'confirm'
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),  # New state
        ('done', 'Done'),
    ], string='Status', default='draft', readonly=True)

    def action_confirm_scrap(self):
        """Phase 1: Complete move to intermediate scrap location and create phase 2 draft"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_('Only draft scraps can be confirmed.'))
            
        if not self.intermediate_scrap_location_id:
            raise UserError(_('Please select an intermediate scrap location.'))
        
        self.state = 'confirm'
        
class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    scrap_id = fields.Many2one(
        'stock.scrap',
        string='Scrap Reference',
        readonly=True,
        help='Reference to the scrap order associated with this move line'
    )
    
    def write(self, vals):
        """Override write to add receipt validation when saving manually"""
        # Call super first untuk save data
        result = super().write(vals)
        
        # Setelah save, lakukan validasi untuk incoming pickings
        for line in self:
            if (line.picking_id and 
                line.picking_id.picking_type_code == 'incoming' and 
                line.picking_id.state in ('draft', 'confirmed', 'assigned') and
                ('quantity' in vals or 'qty_done' in vals)):
                
                # Ambil quantity yang aktif
                active_qty = line.quantity if line.quantity else line.qty_done
                
                if active_qty > line.move_id.product_uom_qty:
                    raise ValidationError(
                        _("Receipt quantity (%.2f) cannot exceed demand quantity (%.2f) for product '%s'. Please adjust the quantity.") % (
                            active_qty,
                            line.move_id.product_uom_qty,
                            line.product_id.display_name
                        )
                    )
                
            # Validasi untuk outgoing pickings
            if (line.picking_id and 
                line.picking_id.picking_type_code == 'outgoing' and 
                line.picking_id.state in ('draft', 'confirmed', 'assigned') and
                ('quantity' in vals or 'qty_done' in vals)):
                
                # Ambil quantity yang aktif
                active_qty = line.quantity if line.quantity else line.qty_done
                
                if active_qty > line.move_id.product_uom_qty:
                    raise ValidationError(
                        _("Delivery quantity (%.2f) cannot exceed demand quantity (%.2f) for product '%s'. Please adjust the quantity.") % (
                            active_qty,
                            line.move_id.product_uom_qty,
                            line.product_id.display_name
                        )
                    )
        
        return result
    
    @api.constrains('quantity', 'qty_done')
    def _check_receipt_quantity_limit(self):
        """Real-time validation: Receipt quantity cannot exceed demand for incoming operations"""
        for line in self:
            if (line.picking_id and 
                line.picking_id.picking_type_code == 'incoming' and 
                line.state not in ('cancel', 'done')):
                
                # Ambil quantity yang aktif (quantity atau qty_done)
                active_qty = line.quantity if line.quantity else line.qty_done
                
                if active_qty > line.move_id.product_uom_qty:
                    raise ValidationError(
                        _("Receipt quantity (%.2f) cannot exceed demand quantity (%.2f) for product '%s'") % (
                            active_qty,
                            line.move_id.product_uom_qty,
                            line.product_id.display_name
                        )
                    )
            # Validasi untuk outgoing pickings
            if (line.picking_id and 
                line.picking_id.picking_type_code == 'outgoing' and 
                line.state not in ('cancel', 'done')):
                
                # Ambil quantity yang aktif (quantity atau qty_done)
                active_qty = line.quantity if line.quantity else line.qty_done
                
                if active_qty > line.move_id.product_uom_qty:
                    raise ValidationError(
                        _("Delivery quantity (%.2f) cannot exceed demand quantity (%.2f) for product '%s'") % (
                            active_qty,
                            line.move_id.product_uom_qty,
                            line.product_id.display_name
                        )
                    )
