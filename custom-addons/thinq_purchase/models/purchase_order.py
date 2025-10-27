from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _auto_set_done_purchase_request(self):
        for rec in self:
            for line in rec.order_line:
                if line.purchase_request_lines:
                    for pr in line.mapped('purchase_request_lines.request_id'):
                        all_purchase_order_lines = pr.mapped('line_ids.purchase_lines')
                        all_purchase_lines_without_cancel = all_purchase_order_lines.filtered(lambda pol: pol.state != 'cancel')
                        qty_product_pol_not_cancel = sum([pol.product_uom_qty for pol in all_purchase_lines_without_cancel]) or 0.0
                        if all([pol.state in ('done','purchase') for pol in all_purchase_order_lines.filtered(lambda pol: pol.state != 'cancel')]) and \
                            all([(prl.product_qty == prl.purchased_qty) or (prl.product_qty == sum([pol.product_uom_qty for pol in prl.mapped('purchase_lines').filtered(lambda pl: pl.state != 'cancel')])) for prl in pr.mapped('line_ids').filtered(lambda l: l.request_state != 'cancel')]):
                            pr.button_done()

    def _check_purchase_qty_less_than_or_equal_request_qty(self):
        for rec in self:
            list_product_over_qty = []
            for line in rec.order_line:
                if line.purchase_request_lines and line.product_qty:
                    current_prl_qty = sum([prl.product_qty for prl in line.purchase_request_lines.filtered(lambda pl: pl.request_state != "rejected")])
                    exist_purchase_qty = sum([pol.product_qty for prl in line.purchase_request_lines for pol in prl.purchase_lines if pol.state in ('done','release','purchase')])
                    if (exist_purchase_qty + line.product_qty) > current_prl_qty:
                        list_product_over_qty.append("%s: RFQ/PO Qty %s || PR Qty %s" % (
                            line.product_id.display_name or line.product_id.name, "{:,.2f}".format((exist_purchase_qty + line.product_qty)), "{:,.2f}".format(current_prl_qty)))
            if list_product_over_qty and len(list_product_over_qty) > 0:
                list_parts = "%s" % _("\n".join(list_product_over_qty)) if list_product_over_qty else ''
                raise ValidationError("Quantity to purchase is not allowed to be greater than purchase request quantity.\n%s" % list_parts)

    def write(self, vals):
        if vals.get('order_line'):
            for order in self:
                order._check_purchase_qty_less_than_or_equal_request_qty()
        res = super(PurchaseOrder, self).write(vals)
        return res

    def button_confirm(self):
        for order in self:
            order._check_purchase_qty_less_than_or_equal_request_qty()
        res = super(PurchaseOrder,self).button_confirm()
        for order in self:
            order._auto_set_done_purchase_request()
        return res

    # Scrap fields
    scrap_ids = fields.One2many(
        'stock.scrap', compute='_compute_scrap_ids', string="Scrap Records", store=False
    )
    scrap_count = fields.Integer(compute='_compute_scrap_ids', string="Scrap Count", store=False)

    @api.depends('picking_ids')
    def _compute_scrap_ids(self):
        for order in self:
            # Include scraps from both receipts and returns
            all_pickings = order.picking_ids

            # Tambahkan return pickings yang terkait dengan purchase order ini
            # Returns biasanya memiliki origin yang mengandung original picking reference
            return_pickings = self.env['stock.picking'].search([
                ('picking_type_code', '=', 'outgoing'),
                ('origin', 'like', '%return%'),
                ('state', '=', 'done')
            ])

            # Filter return pickings yang benar-benar terkait dengan PO ini
            related_returns = return_pickings.filtered(
                lambda r: any(picking.name in r.origin for picking in order.picking_ids)
            )

            all_pickings |= related_returns

            scraps = self.env['stock.scrap'].search([
                ('picking_id', 'in', all_pickings.ids)
            ])
            order.scrap_ids = scraps
            order.scrap_count = len(scraps)

    def action_view_scraps(self):
        self.ensure_one()

        # Get all related pickings including returns
        all_pickings = self.picking_ids

        # Cari return pickings yang terkait
        return_pickings = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'outgoing'),
            ('origin', 'like', '%return%'),
            ('state', '=', 'done')
        ])

        # Filter return pickings yang benar-benar terkait dengan PO ini
        related_returns = return_pickings.filtered(
            lambda r: any(picking.name in r.origin for picking in all_pickings)
        )

        all_pickings |= related_returns

        scraps = self.env['stock.scrap'].search([('picking_id', 'in', all_pickings.ids)])

        if len(scraps) == 1:
            # Jika hanya 1 scrap, buka form view langsung
            return {
                'type': 'ir.actions.act_window',
                'name': _('Scrap Record'),
                'res_model': 'stock.scrap',
                'view_mode': 'form',
                'res_id': scraps.id,
                'target': 'current',
            }
        else:
            # Jika multiple scraps, buka list view dengan fallback
            return {
                'type': 'ir.actions.act_window',
                'name': _('Scrap Records'),
                'res_model': 'stock.scrap',
                'view_mode': 'list,form',  # Ubah dari 'tree,form' ke 'list,form'
                'domain': [('id', 'in', scraps.ids)],  # Lebih spesifik
                'context': {
                    'default_picking_id': self.picking_ids[:1].id if self.picking_ids else False,
                },
                'target': 'current',
            }

    def _add_supplier_to_product(self):
        res = super(PurchaseOrder, self)._add_supplier_to_product()
        for line in self.order_line:
            partner = self.partner_id if not self.partner_id.parent_id else self.partner_id.parent_id
            already_seller = (partner | self.partner_id) & line.product_id.seller_ids.mapped('partner_id')
            if line.product_id and already_seller:
                price = line.price_unit
                if line.product_id.product_tmpl_id.uom_po_id != line.product_uom:
                    default_uom = line.product_id.product_tmpl_id.uom_po_id
                    price = line.product_uom._compute_price(price, default_uom)
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order.date(),
                    uom_id=line.product_uom)
                seller.write({'price': price})
        return res

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    request_line_ref = fields.Char('PR Ref.', compute='_compute_request_line_ref', store=True)
    scrapped_qty = fields.Float(
        string='Scrapped Qty',
        compute='_compute_scrapped_qty',
        store=True,
        digits='Product Unit of Measure'
    )
    qty_received_after_scrap = fields.Float(
        string='Received After Scrap',
        compute='_compute_qty_received_after_scrap',
        store=True,
        digits='Product Unit of Measure',
        help='Quantity received minus scrapped quantity'
    )

    @api.depends('qty_received', 'scrapped_qty')
    def _compute_qty_received_after_scrap(self):
        for line in self:
            line.qty_received_after_scrap = line.qty_received - line.scrapped_qty

    @api.depends(
        'purchase_request_lines.request_id.name',
        'purchase_request_lines.product_qty',
        'purchase_request_lines.product_uom_id'
    )
    def _compute_request_line_ref(self):
        for rec in self:
            rec.request_line_ref = ', '.join([l.request_id.name for l in rec.purchase_request_lines])

    @api.depends('move_ids.state', 'move_ids.picking_id.picking_type_id.is_intermediate_scrap', 'move_ids.product_uom_qty')
    def _compute_scrapped_qty(self):
        for line in self:
            scrapped_qty = 0.0
            for move in line.move_ids:
                if (
                    move.state == 'done'
                    and move.picking_id
                    and getattr(move.picking_id.picking_type_id, 'is_intermediate_scrap', False)
                    and move.purchase_line_id == line
                ):
                    move_qty = move.product_uom._compute_quantity(
                        move.product_uom_qty, line.product_uom
                    )
                    if move.location_dest_id.id == move.picking_type_id.default_location_dest_id.id:
                        scrapped_qty += move_qty
                    else:
                        # handle return scrap
                        scrapped_qty -= move_qty
            line.scrapped_qty = scrapped_qty

    def _get_po_line_moves(self):
        self.ensure_one()
        moves = self.move_ids.filtered(lambda m: m.product_id == self.product_id and not m.picking_type_id.is_intermediate_scrap)
        if self._context.get('accrual_entry_date'):
            moves = moves.filtered(lambda r: fields.Date.context_today(r, r.date) <= self._context['accrual_entry_date'])
        return moves
