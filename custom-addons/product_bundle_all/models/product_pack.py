# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductPack(models.Model):
    _name = 'product.pack'
    _inherit = ['pos.load.mixin']
    _description = "Product Pack"

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["id", "name", "qty_uom", "price", "uom_id", "qty_available", "is_storable"]

    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    qty_uom = fields.Float(string='Quantity', required=True, default=1.0)
    qty_available = fields.Float(related='product_id.qty_available')
    is_storable = fields.Boolean(related='product_id.is_storable')
    bi_product_template = fields.Many2one(comodel_name='product.template', string='Product pack')
    bi_image = fields.Binary(related='product_id.image_1920', store=True, string='Image')
    price = fields.Float(related='product_id.lst_price', store=True, string='Product Price')
    uom_id = fields.Many2one(related='product_id.uom_id', string="Unit of Measure", store=True, readonly=True)
    name = fields.Char(compute='_compute_product_name', store=True)

    @api.depends('product_id.name')
    def _compute_product_name(self):
        for rec in self:
            rec.name = rec.product_id.name

    @api.constrains('qty_uom')
    def _check_reconcile(self):
        for product in self:
            if product.qty_uom < 1:
                raise UserError(_('Product Quantity must be 1 or greater than one'))
