from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
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