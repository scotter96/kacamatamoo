# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from itertools import groupby
from odoo.exceptions import ValidationError, UserError


class RelatedPosStock(models.Model):
    _inherit = 'stock.picking'

    def _prepare_stock_move_vals_for_sub_product(self, first_line, item, order_lines):
        return {
            'name': first_line.name,
            'product_uom': item.product_id.uom_id.id,
            'picking_id': self.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': item.product_id.id,
            'product_uom_qty': item.qty_uom * abs(sum(order_lines.mapped('qty'))),
            'state': 'draft',
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
        }

    def _create_move_from_pos_order_lines(self, lines):
        self.ensure_one()
        lines_by_product = groupby(sorted(lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)
        move_vals = []
        for dummy, olines in lines_by_product:
            order_lines = self.env['pos.order.line'].concat(*olines)
            first_line = order_lines[0]
            if first_line.product_id.pack_ids:
                for item in first_line.product_id.pack_ids:
                    if (item.product_id.type in ['product', 'consu']):
                        current_move = self._prepare_stock_move_vals_for_sub_product(first_line, item, order_lines)
                        move_vals.append(current_move)
            else:
                move_vals.append(self._prepare_stock_move_vals(order_lines[0], order_lines))
        moves = self.env['stock.move'].create(move_vals)
        confirmed_moves = moves._action_confirm()
        confirmed_moves._add_mls_related_to_order(lines, are_qties_done=True)
        confirmed_moves.picked = True
        self._link_owner_on_return_picking(lines)
