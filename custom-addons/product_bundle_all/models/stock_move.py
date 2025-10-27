# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class StockMoveInherit(models.Model):
    _inherit = 'stock.move'

    pack_id = fields.Many2one('product.pack', string="PACK")
