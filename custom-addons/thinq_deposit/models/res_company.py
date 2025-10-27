from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    # Default account untuk customer deposits (liability)
    account_customer_deposit_id = fields.Many2one(
        'account.account',
        string='Customer Deposit Account',
        help='Account for customer deposits (liability account)',
        domain="[('account_type', '=', 'liability_current')]"
    )
    # Default account untuk vendor deposits (asset) 
    account_vendor_deposit_id = fields.Many2one(
        'account.account', 
        string='Vendor Deposit Account',
        help='Account for vendor deposits (asset account)',
        domain="[('account_type', '=', 'asset_current')]"
    )