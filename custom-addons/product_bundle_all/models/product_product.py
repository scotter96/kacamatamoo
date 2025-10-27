# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import math
from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if 'pack_ids' not in fields:
            fields.append('pack_ids')
        if 'is_pack' not in fields:
            fields.append('is_pack')
        return fields

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        res = super(ProductProduct, self)._compute_quantities_dict(lot_id=lot_id, owner_id=owner_id,
                                                                   package_id=package_id, from_date=from_date,
                                                                   to_date=to_date)
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        Quant = self.env['stock.quant'].with_context(active_test=False)
        quants_res = dict((item['product_id'][0], (item['quantity'], item['reserved_quantity'])) for item in
                          Quant.read_group(domain_quant, ['product_id', 'quantity', 'reserved_quantity'],
                                            ['product_id'],orderby="product_id"))
        for product in self.with_context(prefetch_fields=False):
            origin_product_id = product._origin.id
            product_id = product.id
            if not origin_product_id:
                res[product_id] = dict.fromkeys(
                    ['qty_available', 'free_qty', 'incoming_qty', 'outgoing_qty', 'virtual_available'],
                    0.0,
                )
                continue
            rounding = product.uom_id.rounding
            if product.is_pack == True:
                qty_available = 0.0
                incoming_qty = 0.0
                outgoing_qty = 0.0
                virtual_available = 0.0
                for pid in product.pack_ids.filtered(lambda x: x.product_id.type == 'product'):
                    if not pid.qty_uom == 0.0:
                        temp_avail = math.floor(pid.product_id.qty_available / pid.qty_uom)
                        if qty_available == 0.0:
                            qty_available = temp_avail
                        elif qty_available < temp_avail:
                            qty_available = qty_available
                        elif temp_avail < qty_available:
                            qty_available = temp_avail

                        temp_incoming = math.floor(pid.product_id.incoming_qty / pid.qty_uom)
                        if incoming_qty == 0.0:
                            incoming_qty = temp_incoming
                        elif incoming_qty < temp_incoming:
                            incoming_qty = incoming_qty
                        elif temp_incoming < incoming_qty:
                            incoming_qty = temp_incoming

                        temp_outgoing = math.floor(pid.product_id.outgoing_qty / pid.qty_uom)
                        if outgoing_qty == 0.0:
                            outgoing_qty = temp_outgoing
                        elif outgoing_qty < temp_outgoing:
                            outgoing_qty = outgoing_qty
                        elif temp_outgoing < outgoing_qty:
                            outgoing_qty = temp_outgoing

                        temp_virtual = math.floor(pid.product_id.virtual_available / pid.qty_uom)
                        if virtual_available == 0.0:
                            virtual_available = temp_virtual
                        elif virtual_available < temp_virtual:
                            virtual_available = virtual_available
                        elif temp_virtual < virtual_available:
                            virtual_available = temp_virtual
                    else:
                        qty_available = 0.0
                        incoming_qty = 0.0
                        outgoing_qty = 0.0
                        virtual_available = 0.0

                qty_available = qty_available
                incoming_qty = incoming_qty
                outgoing_qty = outgoing_qty
                virtual_available = virtual_available
                reserved_quantity = quants_res.get(product_id, [False, 0.0])[1]
                res[product.id]['qty_available'] = float_round(qty_available,
                                                               precision_rounding=product.uom_id.rounding)
                res[product_id]['free_qty'] = float_round(qty_available - reserved_quantity,
                                                          precision_rounding=rounding)
                res[product.id]['incoming_qty'] = float_round(incoming_qty, precision_rounding=product.uom_id.rounding)
                res[product.id]['outgoing_qty'] = float_round(outgoing_qty, precision_rounding=product.uom_id.rounding)
                res[product.id]['virtual_available'] = float_round(virtual_available,
                                                                   precision_rounding=product.uom_id.rounding)

        return res

    # def write(self, vals):
    #     res = super(ProductProduct, self).write(vals)
    #     for pro in self:
    #         if pro.product_tmpl_id:
    #             pro.product_tmpl_id._onchange_list_price()
    #     return res
