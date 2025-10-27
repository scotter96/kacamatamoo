# -*- coding: utf-8 -*-
from odoo import api, models, fields


class PosOrderRefraction(models.Model):
    _name = 'pos.order.refraction'
    _description = 'Lens Prescription Data for POS Order'
    _rec_name = 'name'
    _order = 'name ASC'

    product_key = fields.Char('Product Key') # use for upsert refraction doang mamen
    product_id = fields.Many2one('product.product', string='Product', domain=[('is_lens', '=', True)])
    p_vitrum_spher = fields.Integer('Product Vitrum Spher', compute="_compute_props")
    p_vitrum_cylndr = fields.Integer('Product Vitrum Cylndr', compute="_compute_props")
    p_add = fields.Integer('Product Add', compute="_compute_props")
    name = fields.Char(string='Lens Name', required=True, help="Name of the lens")
    pos_order_id = fields.Many2one('pos.order', string='POS Order', ondelete='cascade', help="Reference to the POS order")
    frame_name = fields.Char(string='Frame', help="Name or model of the frame used")
    frame_shape_id = fields.Many2one('thinq.frame.shape','Shape',index=True)
    frame_id = fields.Many2one('product.product', domain=[('is_frame', '=', True)], string='Frame', help="Name or model of the frame used")
    side = fields.Selection([('L', 'Left'), ('R', 'Right')], string='Side', help="Lens side: Left or Right")
    vitrum_spher = fields.Integer(string='Vitrum Spher', digits=(6, 2), help="Spherical power of the lens")
    vitrum_cylndr = fields.Integer(string='Vitrum Cylndr', digits=(6, 2), help="Cylindrical power of the lens")
    axis = fields.Integer(string='Axis', digits=(5, 1), help="Axis angle (if applicable)")
    prima_basis = fields.Integer(string='Prima Basis', digits=(4, 2), help="Prism base value (if applicable)")
    add = fields.Integer(string='Add', digits=(4, 2), help="Add power (for multifocal/progressive lenses)")
    pd = fields.Integer(string='PD', digits=(4, 1), help="Pupillary Distance")
    erc = fields.Char(string='Eye Rotation Center (ERC)', help="Eye Rotation Center measurement")
    ocular_dominance = fields.Selection([('Left', 'Left'), ('Right', 'Right')], string='Ocular Dominance (OD)', help="Dominant eye")

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id.is_plano:
            self.vitrum_spher = 0.0
            self.vitrum_cylndr = 0.0
            self.axis = 0.0
            self.prima_basis = 0.0
            self.add = 0.0
            self.pd = 0.0
        else:
            self.vitrum_spher = self.product_id.vitrum_spher
            self.vitrum_cylndr = self.product_id.vitrum_cylndr
            self.add = self.product_id.add
        self.name = self.product_id.name

    @api.onchange('frame_id')
    def onchange_frame_id(self):
        self.frame_name = self.frame_id.name if self.frame_id else ''

    @api.depends('product_id')
    def _compute_props(self):
        for record in self:
            if record.product_id.is_plano:
                record.p_vitrum_spher = 0
                record.p_vitrum_cylndr = 0
                record.p_add = 0
            else:
                record.p_vitrum_spher = record.product_id.vitrum_spher
                record.p_vitrum_cylndr = record.product_id.vitrum_cylndr
                record.p_add = record.product_id.add

    @api.model
    def create_refractions(self, order_ref, product_ids):
        order_id = self.env['pos.order'].sudo().search([
                ('pos_reference', '=', order_ref)
            ], limit=1, order='id desc')

        ids = []
        order_id.refraction_line_ids = [(6,0,[])]
        for _product in product_ids:
            self._create_refraction(ids, _product, order_id, f"{_product.get('product_id', 0)}-{_product.get('line_index', 0)}")
        return ids

    def _create_refraction(self, ids, _product, order_id, product_key):
        refraction_id = self.search([('product_key','=',product_key),('pos_order_id','=',order_id.id)],limit=1)
        if not refraction_id:
            product_id = self.env['product.product'].browse(_product.get('product_id', 0))
            data = {
                'product_key': product_key,
                'product_id': product_id.id,
                'name': product_id.name,
                'pos_order_id': order_id.id,
                'vitrum_spher': 0.0 if product_id.is_plano else product_id.vitrum_spher,
                'vitrum_cylndr': 0.0 if product_id.is_plano else product_id.vitrum_cylndr,
                'axis': 0.0,
                'prima_basis': 0.0,
                'add': 0.0 if product_id.is_plano else product_id.add,
                'pd': 0.0,
            }
            refraction_id = self.create(data)
        
        refract_data = {
            'product_key':refraction_id.product_key,
            'product_id':refraction_id.product_id.id,
            'name':refraction_id.product_id.name,
            'pos_order_id':order_id.id,
            'vitrum_spher':refraction_id.vitrum_spher,
            'vitrum_cylndr':refraction_id.vitrum_cylndr,
            'axis':refraction_id.axis,
            'prima_basis':refraction_id.prima_basis,
            'add':refraction_id.add,
            'pd':refraction_id.pd,
        }
        
        ids.append({
            'id': refraction_id.id,
            'data': refract_data
        })

    @api.model
    def show_refractions(self, order_ref):
        order_id = self.env['pos.order'].sudo().search([
                ('pos_reference', '=', order_ref)
            ], limit=1, order='id desc')

        ids = []

        refraction_ids = self.sudo().search([
                ('pos_order_id', '=', order_id.id)
            ])

        if refraction_ids:
            for obj in refraction_ids:
                data = {
                    'product_id': obj.product_id.id,
                    'name': obj.product_id.name,
                    'frame_id': obj.frame_id.id if obj.frame_id else False,
                    'frame_name': obj.frame_name,
                    'pos_order_id': obj.pos_order_id.id,
                    'vitrum_spher': obj.vitrum_spher,
                    'vitrum_cylndr': obj.vitrum_cylndr,
                    'prima_basis': obj.prima_basis,
                    'axis': obj.axis,
                    'add': obj.add,
                    'pd': obj.pd
                }

                ids.append({
                        'id': obj.id,
                        'data': data
                    })
        return ids

    @api.model
    def available_refractions(self, order_ref):
        ids = []

        order_id = self.env['pos.order'].sudo().search([
                ('pos_reference', '=', order_ref)
            ], limit=1, order='id desc')

        if order_id:
            refraction_ids = self.sudo().search([
                ('pos_order_id', '=', order_id.id)
            ])

            if refraction_ids:
                ids = [obj.id for obj in refraction_ids]

        return ids

    @api.model
    def clean_refractions_data(self, order_ref):
        ids = []

        order_id = self.env['pos.order'].sudo().search([
                ('pos_reference', '=', order_ref)
            ], limit=1, order='id desc')

        if order_id:
            refraction_ids = self.sudo().search([
                ('pos_order_id', '=', order_id.id)
            ])

            if refraction_ids:
                for obj in refraction_ids:
                    obj.unlink()
                return True

        return False

    @api.model
    def action_delete_record(self, ids):
        for id in ids:
            record = self.sudo().browse(id)
            record.unlink()
