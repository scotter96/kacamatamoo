from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    last_sale_date = fields.Datetime(
        'Last Sale Date',
        compute='_compute_last_sale_date',
    )

    inventory_aging = fields.Integer(
        'Inventory Aging (Days)',
        compute='_compute_inventory_aging',
        help="Today - Last Sale Date"
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

    @api.depends('product_id')
    def _compute_last_sale_date(self):
        Move = self.env['stock.move'].with_context(active_test=False)
        for quant in self:
            last_move = Move.search([
                ('product_id', '=', quant.product_id.id),
                ('picking_id.picking_type_id.code', '=', 'outgoing'),
                ('state', '=', 'done'),
            ], order='date desc', limit=1)
            quant.last_sale_date = last_move.picking_id.date_done or False

    @api.depends('last_sale_date')
    def _compute_inventory_aging(self):
        today = fields.Datetime.now()
        for quant in self:
            if quant.last_sale_date:
                delta = today - quant.last_sale_date
                quant.inventory_aging = delta.days
            else:
                quant.inventory_aging = 0