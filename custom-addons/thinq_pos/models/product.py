from odoo import api, fields, models


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += ['is_lens', 'is_frame', 'qty_available']
        return fields
