# -*- coding: utf-8 -*-
from odoo import models, fields


class GaAssetCategory(models.Model):
    _name = 'ga.asset.category'
    _description = 'GA Asset Category Master'

    name = fields.Char('Category Name', required=True, )
    code = fields.Char('Code', size=10, help="e.g., ELE, FUR, KEN")
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Category name must be unique!'),
        ('code_uniq', 'unique(code)', 'Category code must be unique!'),
    ]

    def name_get(self):
        result = []
        for rec in self:
            name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
            result.append((rec.id, name))
        return result