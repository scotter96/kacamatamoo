from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'
    
    # Override field print_format dengan menambahkan selection custom
    print_format = fields.Selection(
        selection_add=[('custom', 'Custom 18x38mm')],  # Updated label size
        ondelete={'custom': 'set default'}
    )
    
    def process(self):
        """Override process untuk handle format custom"""
        if self.print_format == 'custom':
            return self._process_custom_format()
        return super().process()
    
    def _process_custom_format(self):
        """Process custom format 18x38mm"""
        if not self.product_tmpl_ids and not self.product_ids:
            raise UserError(_("You must select at least one product to print labels."))
        
        # Get products to print
        products = self.product_tmpl_ids
        if not products and self.product_ids:
            products = self.product_ids.mapped('product_tmpl_id')
        
        if not products:
            raise UserError(_("No products found to print."))
        
        # Return action seperti shipping label (simple)
        return {
            'type': 'ir.actions.report',
            'report_name': 'thinq_inventory.report_product_label_custom',
            'report_type': 'qweb-pdf',
            'context': dict(self.env.context, custom_quantity=self.custom_quantity),
        }