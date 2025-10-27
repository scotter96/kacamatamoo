from odoo import _, api, fields, models

SEQUENCE_CODE = 'SC'

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        warehouses.sudo().create_missing_scrap_intermediate()
        return warehouses

    def _create_scrap_sequence(self):
        for rec in self:
            seq = self.env['ir.sequence'].sudo().search([
                ('code', '=', f'thinq.stock.scrap.{rec.code}'),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)
            if not seq:
                self.env['ir.sequence'].sudo().create({
                    'name': f'Scrap ({rec.company_id.name})',
                    'code': f'thinq.stock.scrap.{rec.code}',
                    'company_id': rec.company_id.id,
                    'prefix': f'{rec.code}/{SEQUENCE_CODE}/',
                    'padding': 5,
                })

    def _create_intermediate_scrap_loc(self):
        for rec in self:
            loc = self.env['stock.location'].sudo().search([
                ('warehouse_id', '=', rec.id),
                ('barcode', '=', f'INT-SCRAP-{rec.id}')
            ], limit=1)
            if not loc:
                self.env['stock.location'].sudo().create({
                    'name': 'Intermediate for Scrap',
                    'location_id': rec.lot_stock_id.id,
                    'usage': 'internal',
                    'company_id': rec.company_id.id,
                    'warehouse_id': rec.id,
                    'barcode': f'INT-SCRAP-{rec.id}',
                })

    def _create_scrap_picking_type(self):
        for rec in self:
            picking = self.env['stock.picking.type'].sudo().search([
                ('company_id', '=', rec.company_id.id),
                ('warehouse_id', '=', rec.id),
                ('sequence_code', '=', SEQUENCE_CODE),
                ('is_intermediate_scrap', '=', True)
            ], limit=1)
            if not picking:
                sequence = self.env['ir.sequence'].sudo().search([
                    ('code', '=', f'thinq.stock.scrap.{rec.code}'),
                    ('company_id', '=', rec.company_id.id),
                ], limit=1)
                int_scrap_loc = self.env['stock.location'].sudo().search([
                    ('warehouse_id', '=', rec.id),
                    ('barcode', '=', f'INT-SCRAP-{rec.id}')
                ], limit=1)
                self.env['stock.picking.type'].sudo().create({
                    'name': 'Scrap',
                    'company_id': rec.company_id.id,
                    'warehouse_id': rec.id,
                    'sequence_id': sequence.id,
                    'code': 'internal',
                    'default_location_src_id': rec.lot_stock_id.id,
                    'default_location_dest_id': int_scrap_loc.id,
                    'sequence_code': SEQUENCE_CODE,
                    'use_existing_lots': False,
                    'is_intermediate_scrap': True
                })

    def _create_int_scrap_route(self):
        for rec in self:
            route = self.env['stock.route'].sudo().search([
                ('name', '=', f'{rec.name}: Two Step Scrap'),
                ('company_id', '=', rec.company_id.id),
                ('supplied_wh_id', '=', rec.id),
            ], limit=1)
            if not route:
                self.env['stock.route'].sudo().create({
                    'name': f'{rec.name}: Two Step Scrap',
                    'sequence': 20,
                    'supplied_wh_id': rec.id,
                    'company_id': rec.company_id.id,
                    'warehouse_selectable': True,
                    'warehouse_ids': [(6, 0, [rec.id])],
                    'product_selectable': False,
                })

    def _create_scrap_rule(self):
        for rec in self:
            scrap_picking_type = self.env['stock.picking.type'].sudo().search([
                ('company_id', '=', rec.company_id.id),
                ('warehouse_id', '=', rec.id),
                ('sequence_code', '=', SEQUENCE_CODE),
            ], limit=1)
            if not scrap_picking_type:
                continue

            scrap_route = self.env['stock.route'].sudo().search([
                ('name', '=', f'{rec.name}: Two Step Scrap'),
                ('company_id', '=', rec.company_id.id),
                ('supplied_wh_id', '=', rec.id)
            ], limit=1)
            scrap_location = self.env['stock.location'].sudo().search([
                ('company_id', '=', rec.company_id.id),
                ('scrap_location', '=', True)
            ], limit=1)
            int_scrap_loc = self.env['stock.location'].sudo().search([
                ('warehouse_id', '=', rec.id),
                ('barcode', '=', f'INT-SCRAP-{rec.id}')
            ], limit=1)

            # Cek apakah rule sudah ada
            existing_rule = self.env['stock.rule'].sudo().search([
                ('company_id', '=', rec.company_id.id),
                ('route_id', '=', scrap_route.id),
                ('location_src_id', '=', int_scrap_loc.id),
                ('location_dest_id', '=', scrap_location.id),
                ('picking_type_id', '=', scrap_picking_type.id),
            ], limit=1)

            if not existing_rule:
                self.env['stock.rule'].sudo().create({
                    'name': f'{rec.lot_stock_id.name} → {scrap_location.name}',
                    'action': 'push',
                    'location_dest_id': scrap_location.id,
                    'location_src_id': int_scrap_loc.id,
                    'procure_method': 'make_to_stock',
                    'route_id': scrap_route.id,
                    'picking_type_id': scrap_picking_type.id,
                    'company_id': rec.company_id.id,
                })

    @api.model
    def create_missing_scrap_intermediate(self):
        warehouse = self.env['stock.warehouse'].search([])
        warehouse.sudo()._create_int_scrap_route()
        warehouse.sudo()._create_intermediate_scrap_loc()
        warehouse.sudo()._create_scrap_sequence()
        warehouse.sudo()._create_scrap_picking_type()
        warehouse.sudo()._create_scrap_rule()
