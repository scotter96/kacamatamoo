from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AssetLabelLayout(models.TransientModel):
    _name = 'asset.label.layout'
    _description = 'Asset Label Layout Wizard'

    asset_ids = fields.Many2many('account.asset', string='Assets', required=True)
    print_format = fields.Selection([
        ('custom_107', 'Custom Grid 107 (18x50mm)'),  # Grid layout untuk 107
        ('custom_109', 'Custom Grid 109 (13x38mm)'),  # Grid layout untuk 109
    ], string='Label Format', required=True, default='custom_107')
    
    # Field custom_quantity seperti di thinq_inventory
    custom_quantity = fields.Integer(string='Quantity', default=1, required=True)

    def action_print_labels(self):
        if not self.asset_ids:
            raise UserError(_("Please select at least one asset."))
        
        # Handle custom grid formats
        if self.print_format == 'custom_107':
            return self._process_custom_format_107()
        elif self.print_format == 'custom_109':
            return self._process_custom_format_109()
    
    def _process_custom_format_107(self):
        """Process custom grid format untuk 107 (18x50mm)"""
        if not self.asset_ids:
            raise UserError(_("You must select at least one asset to print labels."))
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'thinq_asset.report_asset_label_custom_107',
            'report_type': 'qweb-pdf',
            'context': dict(self.env.context, custom_quantity=self.custom_quantity),
        }
    
    def _process_custom_format_109(self):
        """Process custom grid format untuk 109 (13x38mm)"""
        if not self.asset_ids:
            raise UserError(_("You must select at least one asset to print labels."))
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'thinq_asset.report_asset_label_custom_109',
            'report_type': 'qweb-pdf',
            'context': dict(self.env.context, custom_quantity=self.custom_quantity),
        }