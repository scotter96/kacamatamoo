from odoo import api, fields, models


class LoyaltyProgramInherit(models.Model):
    _inherit = 'loyalty.program'

    check_partner_birthday = fields.Boolean('Check Partner Birthday +7')

    promotion_class_id = fields.Many2one(
        'pos.promotion.class',
        string='Promotion Class',
        help='Menunjukkan Kelas Promotion. Promosi dalam satu kelas yang sama dapat bersifat tiering. '
             'Promosi berbeda kelas tidak dapat digabung menjadi satu.'
    )    
    
    # @api.model
    # def _get_compatible_programs(self, order):
    #     # Override untuk memastikan hanya promosi dari kelas yang sama yang bisa digabung

    #     programs = super()._get_compatible_programs(order)
        
    #     # Jika order sudah memiliki program loyalty dengan promotion_class tertentu
    #     # hanya tampilkan program dengan kelas yang sama
    #     existing_programs = order.applied_coupon_ids.mapped('program_id')
    #     if existing_programs:
    #         existing_classes = existing_programs.mapped('promotion_class')
    #         # Filter hanya yang kelasnya sama
    #         if existing_classes:
    #             main_class = existing_classes[0]  # Ambil kelas pertama
    #             programs = programs.filtered(lambda p: p.promotion_class == main_class)
        
    #     return programs

    # Override field asli
    total_order_count = fields.Integer(
        "Total Order Count", 
        compute="_compute_total_order_count", 
        store=True,  # untuk filter di list view
    )