# models/ga_asset_attribute.py
from odoo import models, fields


class GaAssetAttribute(models.Model):
    _name = 'ga.asset.attribute'
    _description = 'GA Asset Attribute'

    name = fields.Char('Attribute Name', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Attribute name must be unique!'),
    ]


class GaAssetAttributeLine(models.Model):
    _name = 'ga.asset.attribute.line'
    _description = 'GA Asset Attribute Line'

    asset_id = fields.Many2one(
        'account.asset',
        string='Asset',
        ondelete='cascade',
        required=True,
        index=True
    )

    attribute_id = fields.Many2one(
        'ga.asset.attribute',
        string='Attribute',
        required=True
    )

    value = fields.Char('Value')