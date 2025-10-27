# location_based_adjustment/wizards/thinq_inventory_adjustment.py

import base64
import pandas as pd
from io import BytesIO
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ThinqInventoryAdjustment(models.Model):
    _name = 'thinq.inventory.adjustment'
    _description = 'Quick Location-based Inventory Adjustment'

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: _('New'))
    location_id = fields.Many2one(
        'stock.location',
        string='Inventory Location',
        required=True,
        domain="[('usage', '=', 'internal')]",
        help="The specific location where you want to adjust inventory.",
        readonly=True, states={'draft': [('readonly', False)]}
    )
    adjustment_line_ids = fields.One2many(
        'thinq.inventory.adjustment.line',
        'adjustment_id',
        string='Products to Adjust',
        states={'done': [('readonly', True)],'draft': [('readonly', False)]}
    )
    recount_line_ids = fields.Many2many(
        'thinq.inventory.adjustment.line',
        string='Recount Lines (Editable Filter)',
        compute='_compute_recount_lines',
        inverse='_inverse_recount_lines'
    )
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), 
                              ('recount', 'Recount'),
                              ('moved', 'Missing QTY Moved'), 
                              ('done', 'Done'), 
                              ('cancel', 'Cancelled')], string='Status', default='draft', readonly=True, copy=False)
    file_upload = fields.Binary(string="Upload File", states={'draft': [('readonly', False)]})
    file_name = fields.Char(string="File Name")
    date_done = fields.Datetime("Date Done")
    missing_qty_move_ids = fields.Many2many('stock.move', string="Missing QTY moves")
    
    def action_recount(self):
        self.state = 'recount'
    
    def action_draft(self):
        if self.state == 'recount':
            self.state = 'draft'
    
    @api.depends('adjustment_line_ids', 'adjustment_line_ids.qty_counted')
    def _compute_recount_lines(self):
        """
        This method populates our M2M field with only the lines that have a difference.
        """
        for adjustment in self:
            if adjustment.state == 'recount':
                # Filter the source of truth
                lines_with_difference = adjustment.adjustment_line_ids.filtered(
                    lambda line: line.qty_difference != 0
                )
                # Assign the result to our proxy field
                adjustment.recount_line_ids = lines_with_difference

    def _inverse_recount_lines(self):
        """
        This inverse method makes the M2M field editable in the view.
        We don't need to write any logic here because any edits to the fields
        (like qty_counted) are saved directly on the line records themselves,
        not on the relation. This function's existence is all that matters.
        """
        return True

    def action_move_missing_items(self):
        """
        This method handles both moving the items and posting the accounting entries.
        It finds lines where counted quantity is less than on-hand, and creates
        a stock move to a designated 'missing' location.
        Odoo's standard stock move process will automatically handle the creation
        of valuation layers and journal entries if the product is configured
        for automated inventory valuation.
        """
        self.ensure_one()

        # 1. Find the unique "missing" destination location
        missing_location = self.env['stock.location'].search([
            ('is_missing_location', '=', True),
            ('usage','=','internal'),
            ('company_id', '=', self.company_id.id)
        ])
        if not missing_location:
            raise UserError(_("Operation cannot proceed: No 'Missing Location' has been configured. Please check the box on one of your internal stock locations."))
        if len(missing_location) > 1:
            raise UserError(_("Configuration error: There are multiple locations flagged as 'Missing Location'. Please ensure only one is active."))

        source_location = self.location_id
        
        # 2. Filter for lines with a deficit
        lines_with_deficit = self.adjustment_line_ids.filtered(lambda line: line.qty_difference < 0)

        if not lines_with_deficit:
            raise UserError(_("There are no lines with a negative difference to process."))

        StockMove = self.env['stock.move']
        moves_to_process = self.env['stock.move']

        # 3. Prepare stock moves for all deficit lines
        for line in lines_with_deficit:
            # The quantity to move is the absolute value of the negative difference
            qty_to_move = abs(line.qty_difference)

            move_vals = {
                'name': _('Missing Stock: %s') % line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': qty_to_move,
                'product_uom': line.product_uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': missing_location.id,
                'reference': self.name,
                'company_id': self.company_id.id,
            }
            new_move = StockMove.create(move_vals)
            moves_to_process |= new_move
            self.missing_qty_move_ids = [(4,new_move.id)]

        # 4. Process the moves: Confirm -> Assign -> Done
        # This sequence validates the move and triggers the accounting entries.
        if moves_to_process:
            moves_to_process._action_confirm()
            moves_to_process._action_assign()
            # You could add extra checks here for availability if needed, but for
            # moving missing stock, we assume it's logically available to be moved.
            moves_to_process._action_done()

        # After moving, we can set the original adjustment to 'done'
        # and also apply the remaining positive adjustments.
        # self.action_create_inventory_adjustment() # This applies the positive adjustments
        self.write({'state': 'moved'})

        return True
    
    def action_scrap_missing_qty(self):
        """
        Creates and validates stock.scrap records for any lines with a negative difference.
        This directly removes the stock from inventory and creates the accounting entries.
        """
        self.ensure_one()
        lines_with_deficit = self.adjustment_line_ids.filtered(lambda line: line.qty_difference < 0)

        if not lines_with_deficit:
            raise UserError(_("There are no lines with a negative difference to scrap."))

        scrap_location = self.env['stock.location'].search([
            ('scrap_location', '=', True),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not scrap_location:
            raise UserError(_("No default Scrap Location found. Please configure one in your warehouse settings."))

        if not self.missing_qty_move_ids:
            for line in lines_with_deficit:
                qty_to_scrap = abs(line.qty_difference)
                scrap = self.env['stock.scrap'].create({
                    'product_id': line.product_id.id,
                    'scrap_qty': qty_to_scrap,
                    'product_uom_id': line.product_uom_id.id,
                    'location_id': self.location_id.id,
                    'scrap_location_id': scrap_location.id,
                    'origin': self.name,
                })
                scrap.action_validate() # This validates the scrap AND posts the journal entry
        if self.missing_qty_move_ids:
            for move in self.missing_qty_move_ids:
                qty_to_scrap = abs(move.product_uom_qty)
                scrap = self.env['stock.scrap'].create({
                    'product_id': move.product_id.id,
                    'scrap_qty': qty_to_scrap,
                    'product_uom_id': move.product_id.product_tmpl_id.product_uom_id.id,
                    'location_id': move.location_id.id,
                    'scrap_location_id': scrap_location.id,
                    'origin': self.name,
                })
                scrap.action_validate() 

        self.write({'state': 'done', 'date_done': fields.Datetime.now()})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Assigns a sequence number on creation."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('thinq.inventory.adjustment') or _('New')
        return super().create(vals_list)

    def action_import_from_file(self):
        """
        Reads an uploaded Excel/CSV file and populates the adjustment lines.
        This function is triggered by a button on the view.
        """
        self.ensure_one()
        if not self.file_upload:
            raise UserError(_("Please upload a file first."))

        # Decode the file and read it using pandas
        try:
            file_data = base64.b64decode(self.file_upload)
            if self.file_name.endswith('.xlsx'):
                df = pd.read_excel(BytesIO(file_data))
            elif self.file_name.endswith('.csv'):
                df = pd.read_csv(BytesIO(file_data))
            else:
                raise UserError(_("Unsupported file format. Please use .xlsx or .csv"))
        except Exception as e:
            raise UserError(_("Failed to read file: %s") % e)

        # Validate that the required columns exist in the file
        required_columns = ['product_code', 'counted_quantity']
        if not all(col in df.columns for col in required_columns):
            raise ValidationError(_("File must contain columns: %s") % ", ".join(required_columns))

        lines_to_create = []
        ProductProduct = self.env['product.product']
        
        # Process each row in the file
        for index, row in df.iterrows():
            product_code = row['product_code']
            counted_quantity = row['counted_quantity']

            if not product_code:
                continue # Skip empty rows

            product = ProductProduct.search([('default_code', '=', str(product_code))], limit=1)
            if not product:
                raise UserError(_("Product with internal reference '%s' not found in the system.") % product_code)

            lines_to_create.append({
                'adjustment_id': self.id,
                'product_id': product.id,
                'qty_counted': float(counted_quantity),
            })
        
        # For simplicity, clear existing lines before adding new ones from the file
        self.adjustment_line_ids.unlink()
        self.env['thinq.inventory.adjustment.line'].create(lines_to_create)
        
        # Clear the binary field after successful import
        self.file_upload = False
        self.file_name = False

    def action_create_inventory_adjustment(self):
        """
        Applies inventory adjustments by setting the `inventory_quantity`
        on the correct stock.quant, which is the standard Odoo method.
        """
        self.ensure_one()
        if not self.adjustment_line_ids:
            raise UserError(_("You must add at least one product to adjust."))

        for line in self.adjustment_line_ids:
            # Skip lines where the quantity hasn't changed.
            if line.qty_on_hand == line.qty_counted:
                continue

            # Find the specific quant for the product in the location (assuming no lots/packages).
            quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', self.location_id.id),
                ('lot_id', '=', False),
                ('package_id', '=', False),
                ('owner_id', '=', False),
            ], limit=1)

            if quant:
                # If a quant exists, writing to `inventory_quantity` triggers the update.
                quant.inventory_quantity = line.qty_counted
                quant._apply_inventory()
            else:
                # If no quant exists (on-hand is 0), create a new one.
                # The `inventory_mode` context is key to allow creating a quant
                # and applying the initial inventory.
                quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
                    'product_id': line.product_id.id,
                    'location_id': self.location_id.id,
                    'inventory_quantity': line.qty_counted,
                })
                quant._apply_inventory()

        self.write({'state': 'done','date_done': datetime.now()})
        return True

class ThinqInventoryAdjustmentLine(models.Model):
    """
    Represents a single line in the location adjustment.
    This class is defined FIRST to ensure it's available when the main model is loaded.
    """
    _name = 'thinq.inventory.adjustment.line'
    _description = 'Line for Quick Location-based Inventory Adjustment'

    adjustment_id = fields.Many2one('thinq.inventory.adjustment', string='Adjustment Reference', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    default_code = fields.Char(string='SKU Code', related='product_id.default_code')
    location_id = fields.Many2one(related='adjustment_id.location_id', store=True)
    qty_on_hand = fields.Float(string='On-Hand Quantity', readonly=True, compute='_compute_on_hand', digits='Product Unit of Measure')
    qty_counted = fields.Float(string='Counted Quantity', required=True, digits='Product Unit of Measure', default=0.0)
    qty_difference = fields.Float(string='Difference', readonly=True, compute='_compute_recalculate', store=True, digits='Product Unit of Measure')
    qty_sales = fields.Float(string="Sales Qty", compute="_get_quantity_sold")
    qty_final = fields.Float(string="Qty On Hand (Final)")
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', readonly=True)
    
    def _get_quantity_sold(self):
        """
        Calculates the total sold quantity for a given product within an optional date range.
        :param product_id: The product.product record for which to calculate the sales.
        :param start_date: The start date of the period (optional).
        :param end_date: The end date of the period (optional).
        :return: The total quantity sold as a float.
        """
        for rec in self:
            product_id = rec.product_id
            start_date = "2024-01-01"
            end_date = datetime.now()
            if not product_id:
                return 0.0
            # Define the domain to filter sale order lines
            domain = [
                ('product_id', '=', product_id.id),
                ('order_id.state', 'in', ['sale', 'done']) # Only include confirmed sales
            ]
            # Add date range to the domain if specified
            if start_date:
                domain.append(('order_id.date_order', '>=', start_date))
            if end_date:
                domain.append(('order_id.date_order', '<=', end_date))
            # Search for the sale order lines matching the domain
            order_lines = self.env['sale.order.line'].search(domain)
            # Sum the quantities from the found lines
            total_sold = sum(line.product_uom_qty for line in order_lines)
            rec.qty_sales = total_sold

    @api.depends('product_id', 'location_id')
    def _compute_on_hand(self):
        """
        Computes the on-hand quantity for the product in the specified location.
        """
        for line in self:
            if not line.product_id or not line.location_id:
                line.qty_on_hand = 0.0
                continue
            
            # Use the product's own method to get quantity, which is more robust
            line.qty_on_hand = line.product_id.with_context(location=line.location_id.id).qty_available

    @api.depends('qty_on_hand', 'qty_counted')
    def _compute_recalculate(self):
        """Computes the difference between new and on-hand quantities."""
        for line in self:
            line.qty_difference = line.qty_counted - line.qty_on_hand