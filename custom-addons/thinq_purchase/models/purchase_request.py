from odoo import _, api, fields, models

class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ['purchase.request', 'portal.mixin']

    description = fields.Text('Additional Notes')
    date_start = fields.Date(string='Request Date')
    date_planned = fields.Datetime(string='Expected Date')

    @api.onchange('date_planned')
    def _onchange_date_planned(self):
        for line in self.line_ids:
            if self.date_planned:
                line.date_required = self.date_planned
            else:
                line.date_required = self.date_start

    def _compute_access_url(self):
        super()._compute_access_url()
        for pr in self:
            pr.access_url = '/my/pr/%s' % (pr.id)

    def _get_report_base_filename(self):
        self.ensure_one()
        return f"Purchase Request {self.name or ''}"

class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    price_unit = fields.Monetary('Unit Price')
    estimated_cost = fields.Monetary(compute='_compute_subtotal', store=True)
    date_required = fields.Date('Expected Date')

    @api.onchange('request_id.date_planned', 'request_id')
    def _onchange_date_required(self):
        self.date_required = self.request_id.date_planned or self.request_id.date_start

    @api.depends('product_qty','price_unit')
    def _compute_subtotal(self):
        for rec in self:
            rec.estimated_cost = rec.product_qty * rec.price_unit

    @api.depends('purchase_request_allocation_ids.requested_product_uom_qty')
    def _compute_purchased_qty(self):
        for rec in self:
            rec.purchased_qty = 0.0
            for line in rec.purchase_request_allocation_ids.filtered(lambda l:l.purchase_request_line_id.id == rec.id and l.purchase_line_id.state != 'cancel'):
                if rec.product_uom_id and line.product_uom_id != rec.product_uom_id:
                    rec.purchased_qty += line.product_uom_id._compute_quantity(
                        line.requested_product_uom_qty, rec.product_uom_id
                    )
                else:
                    rec.purchased_qty += line.requested_product_uom_qty