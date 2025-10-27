from odoo import models


class PosCategory(models.Model):
    _inherit = 'pos.category'

    def name_get(self):
        def get_names(category):
            res = []
            while category and len(res) < 3:  
                res.append(category.name)
                category = category.parent_id
            return ' / '.join(reversed(res))

        return [(category.id, get_names(category)) for category in self]