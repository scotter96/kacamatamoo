# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import math
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_pack = fields.Boolean(string='Is Product Pack')
    cal_pack_price = fields.Boolean(string='Calculate Pack Price')
    pack_ids = fields.One2many(comodel_name='product.pack', inverse_name='bi_product_template', string='Product pack')

    @api.onchange('is_pack')
    def _onchange_is_pack(self):
        if not self.is_pack and self.pack_ids:
            self.pack_ids = [(6,0,[])]

    @api.onchange('cal_pack_price')
    def _onchange_cal_pack_price(self):
        if self.cal_pack_price:
            self.list_price = sum(pack.product_id.list_price for pack in self.pack_ids)

    @api.onchange('list_price')
    def _onchange_list_price(self):
        if not self.is_pack or not self.cal_pack_price:
            return
        total = sum(
            (line.product_id.list_price or 0.0) * (line.qty_uom or 1.0)
            for line in self.pack_ids
        )
        self.list_price = total

    # @api.model
    # def create(self, vals):
    #     total = 0
    #     res = super(ProductTemplate, self).create(vals)
    #     if res.cal_pack_price:
    #         if 'pack_ids' in vals or 'cal_pack_price' in vals:
    #             for pack_product in res.pack_ids:
    #                 qty = pack_product.qty_uom
    #                 price = pack_product.product_id.list_price
    #                 total += qty * price
    #     if total > 0:
    #         res.list_price = total
    #     return res

    # def write(self, vals):
    #     total = 0
    #     res = super(ProductTemplate, self).write(vals)
    #     for pk in self:
    #         if pk.cal_pack_price:
    #             if 'pack_ids' in vals or 'cal_pack_price' in vals:
    #                 for pack_product in pk.pack_ids:
    #                     qty = pack_product.qty_uom
    #                     price = pack_product.product_id.list_price
    #                     total += qty * price
    #     if total > 0:
    #         self.list_price = total
    #     return res

    def _compute_quantities_dict(self):
        prod_available = super(ProductTemplate, self)._compute_quantities_dict()
        for template in self:
            incoming_qty = 0
            outgoing_qty = 0
            if template.is_pack == True:
                qty_available = 0.0
                virtual_available = 0.0
                for pid in template.pack_ids.filtered(lambda x: x.product_id.type == 'product'):
                    if not pid.qty_uom == 0.0:
                        temp = math.floor(pid.product_id.qty_available / pid.qty_uom)
                        temp2 = math.floor(pid.product_id.virtual_available / pid.qty_uom)

                        if qty_available == 0.0:
                            qty_available = temp
                        elif qty_available < temp:
                            qty_available = qty_available
                        elif temp < qty_available:
                            qty_available = temp

                        if virtual_available == 0.0:
                            virtual_available = temp2
                        elif virtual_available < temp2:
                            virtual_available = virtual_available
                        elif temp2 < virtual_available:
                            virtual_available = temp2
                    else:
                        qty_available = 0.0
                        virtual_available = 0.0

                    incoming_qty += pid.product_id.incoming_qty
                    outgoing_qty += pid.product_id.outgoing_qty

                qty_available = qty_available
                virtual_available = virtual_available
                prod_available[template.id] = {
                    "qty_available": qty_available,
                    "virtual_available": virtual_available,
                    "incoming_qty": incoming_qty,
                    "outgoing_qty": outgoing_qty,
                }
        return prod_available
