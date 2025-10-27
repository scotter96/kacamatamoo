from odoo import models, fields, _, api, SUPERUSER_ID
from collections import defaultdict
from odoo.tools.float_utils import float_round

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    is_frame = fields.Boolean(
        string='Is Frame',
        default=False,
        help='Penanda apabila produk merupakan frame'
    )

    is_plano = fields.Boolean(
        string='Is Plano',
        default=False,
        help='Penanda pengisian manual spesifikasi produk di POS'
    )
    
    is_lens = fields.Boolean(
        string='Is Lens',
        default=False,
        help='Penanda apabila produk merupakan lensa'
    )
    
    supplier_sku = fields.Char(
        string='Supplier SKU',
        help='Kode produk dari supplier (umum untuk semua produk)'
    )

    # Frame-specific fields
    material_id = fields.Many2one(
        'thinq.material',
        string='Material',
        help='Bahan Frame, e.g. Titanium, Metal, Plastic (khusus untuk Frame)'
    )
    
    color_id = fields.Many2one(
        'thinq.color',
        string='Color',
        help='Warna Frame, e.g. Black, Red, Green (khusus untuk Frame)'
    )

    frame_shape_id = fields.Many2one(
        'thinq.frame.shape',
        string='Frame Shape',
        help='Bentuk Frame, e.g. Round, Square (khusus untuk Frame)'
    )

    rim_size = fields.Float(
        string='Rim Size (mm)',
        help='Lebar Horizontal Frame dalam mm (khusus untuk Frame)',
        digits=(5, 1)
    )
    
    bridge_size = fields.Float(
        string='Bridge Size (mm)',
        help='Ukuran Jembatan Hidung dalam mm (khusus untuk Frame)',
        digits=(5, 1)
    )
    
    temple_size = fields.Float(
        string='Temple Size (mm)',
        help='Ukuran tangkai Frame dalam mm (khusus untuk Frame)',
        digits=(5, 1)
    )
    
    weight = fields.Float(
        string='Weight (gr)',
        help='Berat Frame dalam gr (khusus untuk Frame)',
        digits=(5, 1)
    )
    
    # Lens-specific fields (internal only)
    brand_id = fields.Many2one(
        'thinq.brand',
        string='Brand',
        help='Merek Lensa, e.g. Essilor Crizal, Optimoo L07 (khusus untuk Lensa)'
    )

    vitrum_spher = fields.Integer(
        string='Vitrum Spherical',
        help='Nilai spherical Lensa (khusus untuk Lensa, hanya internal)',
    )
    
    vitrum_cylndr = fields.Integer(
        string='Vitrum Cylinder',
        help='Nilai cylinder Lensa (khusus untuk Lensa, hanya internal)',
    )

    add = fields.Integer(
        string='Add',
    )

    def _force_default_tax(self, companies):
        #FIXME: soon to be fixed, aneh ketika di dev kena record rule di db clean ga kena meskipun companynya > 1
        return True


    @api.onchange('is_plano')
    def _onchange_is_plano(self):
        """Ketika is_plano = True, set vitrum_spher dan vitrum_cylndr = 0.00"""
        if self.is_plano:
            self.vitrum_spher = 0.00
            self.vitrum_cylndr = 0.00
            self.add = 0.00


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Inherit field dari template (otomatis)
    # Pastikan bisa diakses via product_id.primary_location_id

    reserved_quantity = fields.Float(
        'Reserved Stock',
        compute='_compute_reserved_quantity',
        digits='Product Unit of Measure',
        store=True
    )
    entity_id = fields.Many2one('res.company', string='Entity', compute='get_entity', store=True)
    branch_id = fields.Many2one('res.company', string='Branch', compute='get_entity', store=True)
    
    @api.depends('company_id')
    def get_entity(self):
        for rec in self:
            company_id = rec.env.user.company_id.id
            branch_id = False
            if rec.company_id and rec.company_id.parent_id:
                company_id = rec.company_id.sudo().parent_id.id
                branch_id = rec.company_id.id
            elif rec.company_id and not rec.company_id.parent_id:
                company_id = rec.company_id.id
            rec.entity_id = company_id
            rec.branch_id = branch_id
    
    @api.depends('stock_quant_ids.reserved_quantity')
    def _compute_reserved_quantity(self):
        for rec in self:
            qty = 0
            if rec.stock_quant_ids:
                qty = sum(rec.stock_quant_ids.mapped('reserved_quantity'))
            rec.reserved_quantity = qty
