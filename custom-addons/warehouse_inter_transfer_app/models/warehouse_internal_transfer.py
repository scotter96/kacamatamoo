from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductOperations(models.Model):
    _name = "product.operations"
    _description = "Product Operations"

    product_id = fields.Many2one('product.product', string="Product", required=True)
    demand_qty = fields.Float(string="Demand Quantity", default=1.0, required=True)
    inter_war_trans_id = fields.Many2one('inter.tranfer', string="Transfer Reference")
    product_uom_id = fields.Many2one(related='product_id.uom_id', string="UoM", readonly=True)

class InterTransfer(models.Model):
    _name = 'inter.tranfer'
    _description = "Inter Transfer"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = 'id desc'

    is_picking = fields.Boolean(string="Has Picking")
    approve_by_manager = fields.Boolean(string="Approve by Manager", related="company_id.approve_by_manager", readonly=True)
    picking_ids = fields.Many2many('stock.picking', 'inter_picking_default_rel', 'inter_war_id', 'picking_id', string="Pickings", copy=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('waiting', 'Waiting'),
        ('cancel', 'Cancel'),
        ('done', 'Done')
    ], default='draft', string='State')
    name = fields.Char(string='Transfer Reference', required=True, default='New', copy=False, readonly=True)
    partner_id = fields.Many2one(
        'res.partner',
        string="Deliver To",
        required=True,
        domain=lambda self: self._get_partner_domain()
    )

    def _get_partner_domain(self):
        """Domain untuk partner_id - hanya company yang punya warehouse"""
        try:
            # Pastikan context fresh untuk setiap call
            warehouses = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([])
            if not warehouses:
                return [('id', '=', False)]  # Return empty domain kl ga ada warehouse
            
            # Ambil company yang punya warehouse
            company_ids = warehouses.mapped('company_id').ids
            
            # Cari company records dengan sudo dan active_test=False
            companies = self.env['res.company'].sudo().with_context(active_test=False).search([('id', 'in', company_ids)])
            
            # Ambil partner dari company tersebut
            partner_ids = companies.mapped('partner_id').ids
            
            if not partner_ids:
                return [('id', '=', False)]
            
            # Return domain yang include semua partner (aktif dan non-aktif)
            domain = [
                ('is_company', '=', True),
                ('id', 'in', partner_ids)
            ]
            return domain
            
        except Exception as e:
            return [('id', '=', False)]
        
    picking_type_id = fields.Many2one('stock.picking.type', string="Operation Type", required=True, domain="[('code', '=', 'outgoing'), ('name', 'not ilike', 'PoS'), ('name', 'not ilike', 'Point of Sale')]")
    
    @api.onchange('picking_type_id')
    def _onchange_pick_type(self):
        if self.picking_type_id:
            self.location_id = self.picking_type_id.default_location_src_id.id
    
    location_id = fields.Many2one('stock.location', string="Source Location", required=True, domain="[('usage','=', 'internal')]")
    
    location_dest_id = fields.Many2one(
        'stock.location', 
        string="Destination Location", 
        required=True,
    )
    
    @api.model
    def default_transit_location(self):
        return self.env['stock.location'].search([('usage','=','transit')],limit=1)

    transit_location_id = fields.Many2one('stock.location', string="Transit Location", required=True, domain="[('usage', '=', 'transit')]", default=default_transit_location)
    product_opt_ids = fields.One2many('product.operations', 'inter_war_trans_id', string="Products/Operations")
    internal_note = fields.Text(string="Notes")
    is_generate = fields.Boolean(string="Ready to Generate")

    # Field computed untuk dynamic domain
    location_dest_domain = fields.Char(
        string="Location Destination Domain",
        compute="_compute_location_dest_domain"
    )

    @api.depends('partner_id')
    def _compute_location_dest_domain(self):
        """Compute domain untuk location_dest_id berdasarkan partner_id"""
        for record in self:
            # clear location_dest_id tiap kali partner_id berubah
            if record.partner_id:
                # Clear location_dest_id
                record.location_dest_id = False

                target_company = self.env['res.company'].sudo().search([
                    '|', '|',
                    ('partner_id', '=', record.partner_id.id),
                    ('name', '=', record.partner_id.name),
                    ('name', 'ilike', record.partner_id.name)
                ], limit=1)
                
                if target_company:
                    target_warehouse = self.env['stock.warehouse'].sudo().search([
                        ('company_id', '=', target_company.id)
                    ], limit=1)
                    
                    if target_warehouse:
                        # auto populate dg main stock location
                        record.location_dest_id = target_warehouse.lot_stock_id
                        
                        allowed_locations = self.env['stock.location'].search([
                            ('warehouse_id', '=', target_warehouse.id),
                            ('usage', '=', 'internal')
                        ])
                        
                        if allowed_locations:
                            record.location_dest_domain = str([('id', 'in', allowed_locations.ids)])
                        else:
                            record.location_dest_domain = str([('id', '=', False)])
                    else:
                        record.location_dest_domain = str([('id', '=', False)])
                else:
                    record.location_dest_domain = str([('id', '=', False)])
            else:
                # if partner kosong then clear location_dest_id dan set default domain
                record.location_dest_id = False
                record.location_dest_domain = str([('usage', '=', 'internal')])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('inter.tranfer') or 'New'
    
        res = super(InterTransfer, self).create(vals_list)

        for record in res:
            if record.company_id.approve_by_manager and record.state == 'draft':
                record.is_generate = False
            if not record.company_id.approve_by_manager and record.state == 'draft':
                record.is_generate = True

        return res

    def approve_transfer(self):
        if not self.product_opt_ids:
            raise ValidationError(_("Please define products or operations lines...!"))
        if self.company_id.approve_by_manager and self.env.user.has_group('stock.group_stock_manager'):
            self.write({'state': 'approve'})
        if self.company_id.approve_by_manager and self.state == 'approve':
            self.write({'is_generate': True})

    def cancel_transfer(self):
        self.write({'state': 'cancel', 'is_generate': False})
        if self.picking_ids:
            self.picking_ids.action_cancel()

    def generate_internal_transfer(self):
        if not self.product_opt_ids:
            raise ValidationError(_("Please define products or operations lines...!"))
        picking_list = []

        # Outgoing Picking (DO) - sudo untuk bypass multi-company
        vals = {
            'scheduled_date': datetime.now(),
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.transit_location_id.id,
            'move_type': 'direct',
            'inter_war_tr_id': self.id,
            'origin': self.name,
            'name': self.picking_type_id.sudo().sequence_id.next_by_id()
        }
        pick_id = self.env['stock.picking'].sudo().create(vals)

        # Dictionary untuk menyimpan move outgoing berdasarkan product
        outgoing_moves = {}
        
        for line in self.product_opt_ids:
            mv = self.env['stock.move'].sudo().create({
                'name': line.product_id.display_name,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': pick_id.id,
                'picking_type_id': self.picking_type_id.id,
                'product_id': line.product_id.id,
                'product_uom_qty': abs(line.demand_qty),
                'state': 'draft',
                'location_id': self.location_id.id,
                'location_dest_id': self.transit_location_id.id,
            })
            
            outgoing_moves[line.product_id.id] = mv
            
            mvl = self.env['stock.move.line'].sudo().create({
                'picking_id': pick_id.id,
                'location_id': pick_id.location_id.id,
                'location_dest_id': pick_id.location_dest_id.id,
                'quantity': line.demand_qty,
                'product_id': line.product_id.id,
                'move_id': mv.id,
                'product_uom_id': line.product_id.uom_id.id,
            })
    
        pick_id.sudo().action_confirm()
        picking_list.append(pick_id.id)

        # Incoming Picking (GR) - pakai sudo jg
        # Ambil picking type incoming dari warehouse tujuan
        target_warehouse = self.location_dest_id.sudo().warehouse_id
        if not target_warehouse:
            raise ValidationError(_("Destination location must belong to a warehouse!"))
    
        incoming_picking_type = target_warehouse.in_type_id
        if not incoming_picking_type:
            raise ValidationError(_("No incoming picking type found for destination warehouse!"))
    
        # pakai context dari target company untuk incoming picking
        incoming_picking_vals = {
            'scheduled_date': datetime.now(),
            'picking_type_id': incoming_picking_type.id,
            'location_id': self.transit_location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'move_type': 'direct',
            'inter_war_tr_id': self.id,
            'origin': self.name,
            'name': incoming_picking_type.sudo().sequence_id.next_by_id(),
            'company_id': target_warehouse.company_id.id 
        }
    
        # Create dengan context company yang tepat
        picking2 = self.env['stock.picking'].sudo().with_context(
            force_company=target_warehouse.company_id.id,
            allowed_company_ids=[target_warehouse.company_id.id, self.env.company.id]
        ).create(incoming_picking_vals)
        
        # Create moves untuk incoming picking dengan context yang tepat
        for line in self.product_opt_ids:
            orig_move = outgoing_moves.get(line.product_id.id)
            
            # Create move dengan context company yang tepat
            incoming_move_vals = {
                'name': line.product_id.display_name,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking2.id,
                'picking_type_id': incoming_picking_type.id,
                'product_id': line.product_id.id,
                'product_uom_qty': abs(line.demand_qty),
                'location_id': self.transit_location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'move_orig_ids': [(4, orig_move.id)] if orig_move else [],
                'company_id': target_warehouse.company_id.id
            }
            
            mv2 = self.env['stock.move'].sudo().with_context(
                force_company=target_warehouse.company_id.id,
                allowed_company_ids=[target_warehouse.company_id.id, self.env.company.id]
            ).create(incoming_move_vals)
            
            # Create move line dengan context yang tepat
            incoming_move_line_vals = {
                'picking_id': picking2.id,
                'location_id': picking2.location_id.id,
                'location_dest_id': picking2.location_dest_id.id,
                'quantity': line.demand_qty,
                'product_id': line.product_id.id,
                'move_id': mv2.id,
                'product_uom_id': line.product_id.uom_id.id,
                'company_id': target_warehouse.company_id.id  
            }
            
            mvl2 = self.env['stock.move.line'].sudo().with_context(
                force_company=target_warehouse.company_id.id,
                allowed_company_ids=[target_warehouse.company_id.id, self.env.company.id]
            ).create(incoming_move_line_vals)
            
        picking_list.append(picking2.id)

        if pick_id.state in ('confirmed', 'assigned'):
            self.write({'state': 'waiting'})
        self.write({'is_generate': False, 'is_picking': True, 'picking_ids': [(6, 0, picking_list)]})
        
    def action_view_generated_transfer(self):
        picking = self.env['stock.picking'].search([('id', 'in', self.picking_ids.ids)])
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if picking:
            action['domain'] = [('id', 'in', picking.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def unlink(self):
        if self.env.user.has_group('stock.group_stock_manager'):
            return super(InterTransfer, self).unlink()
        else:
            raise ValidationError(_("Delete access have only for Inventory Manager..!"))

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    inter_war_tr_id = fields.Many2one("inter.tranfer", string="Inter Warehouse Transfer", readonly=True)

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        
        if self.inter_war_tr_id and self.picking_type_id.code == 'outgoing':
            incoming_pickings = self.env['stock.picking'].search([
                ('inter_war_tr_id', '=', self.inter_war_tr_id.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', 'in', ['draft', 'waiting'])
            ])
            
            for incoming_pick in incoming_pickings:
                if incoming_pick.state == 'draft':
                    incoming_pick.sudo().action_confirm()
                if incoming_pick.state in ['confirmed', 'waiting']:
                    incoming_pick.sudo().action_assign()
        
        if self.inter_war_tr_id:
            pickings = self.env['stock.picking'].search([('inter_war_tr_id', '=', self.inter_war_tr_id.id)])
            if all(pick.state == 'done' for pick in pickings):
                self.inter_war_tr_id.write({'state': 'done'})
        
        return res