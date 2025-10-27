from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)

STATES = [
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('done', 'Done'),
    ('cancelled', 'Cancelled'),
]

PETTY_CASH_TYPE = [
    ('replenish', 'Replenish'),
    ('usage', 'Usage'),
]

class PettyCash(models.Model):
    _name = 'petty.cash'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _description = 'Petty Cash Management'
    _order = 'id, name desc'

    name = fields.Char(string='Name', index=True, readonly=True, required=True, copy=False, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Responsible', required=True, default=lambda self: self.env.user.partner_id)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    state = fields.Selection(STATES, string='Status', default=STATES[0][0], required=True, copy=False)
    note = fields.Text(string='Note', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    petty_cash_type = fields.Selection(PETTY_CASH_TYPE, string='Petty Cash Type', required=True)
    product_id = fields.Many2one('product.product', string='Product', domain=[('is_petty_cash','=',True)]) # domain is_petty_cash=True
    price_unit = fields.Monetary(string='Unit Price', currency_field='currency_id', required=True)
    qty = fields.Float(string='Qty', default=1.0, digits='Product Unit of Measure')
    invoiced_qty = fields.Float(string='Invoiced Qty', compute='_compute_invoiced_qty', store=True)
    move_line_ids = fields.One2many('account.move.line', 'petty_cash_id', string='Invoice Lines', copy=False)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_price_subtotal', store=True, currency_field='currency_id')
    is_claimed = fields.Selection([
        ('not_claimed', 'Not Claimed'),
        ('claimed', 'Claimed'),
    ], string='Claim Status', default='not_claimed', tracking=True, compute='_compute_claimed_status', store=True)
    analytic_distribution = fields.Json(
        string='Analytic Distribution',
        default=dict,
        widget='analytic_distribution',
        help="Analytic distribution for this petty cash.",
        compute='_compute_analytic_distribution',
        store=True
    )

    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                raise ValidationError(_("You can only delete records in 'Draft' or 'Cancelled' state."))
        return super(PettyCash, self).unlink()
    
    def _sequence_number(self):
        if self.name in [False, _('New')]:
            self.name = self.env['ir.sequence'].with_context(ir_sequence_date=self.date).next_by_code('seq.petty.cash') or _('New')
    
    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_("Only records in 'Draft' state can be confirmed."))
            record._sequence_number()
            record.state = 'confirmed'
            _logger.info("Petty Cash %s confirmed.", record.name)
    
    def action_draft(self):
        for record in self:
            if record.state != 'cancelled':
                raise ValidationError(_("Only records not in 'Cancelled' state can be reverted to 'Draft'."))
            record.state = 'draft'
            _logger.info("Petty Cash %s reverted to Draft state.", record.name)
    
    def action_cancel(self):
        for record in self:
            if record.state not in ['draft', 'confirmed']:
                raise ValidationError(_("Only records in 'Draft' or 'Confirmed' state can be cancelled."))
            record.state = 'cancelled'
            _logger.info("Petty Cash %s cancelled.", record.name)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.note = self.product_id.display_name
            self.price_unit = self.product_id.standard_price
            self.qty = 1.0
            self.uom_id = self.product_id.uom_po_id.id

    @api.depends('price_unit', 'qty')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.price_unit * line.qty

    @api.depends('move_line_ids.quantity', 'move_line_ids.parent_state')
    def _compute_invoiced_qty(self):
        for line in self:
            line.invoiced_qty = sum(inv_line.quantity for inv_line in line.move_line_ids if inv_line.parent_state not in ['cancel', 'draft'])

    def action_view_invoice(self, invoice_ids=None):
        invoices = invoice_ids or self.move_line_ids.mapped('move_id')
        if invoices:
            action = self.env.ref('account.action_move_in_invoice').read()[0]
            if len(invoices) == 1:
                action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
                action['res_id'] = invoices.id
            else:
                action['domain'] = [('id', 'in', invoices.ids)]
            return action

    def _create_invoice(self):
        if self.filtered(lambda x: x.state not in ['confirmed'] or x.petty_cash_type != 'usage'):
            raise ValidationError(_("Only records in 'Confirmed' state and type is 'Usage' can be invoiced."))
        
        grouped = defaultdict(lambda: self.env[self._name])
        for rec in self:
            grouped[rec.company_id] |= rec
        
        created_invoices = self.env['account.move']
        for company, records in grouped.items():
            invoice_vals = records._prepare_invoice()
            invoice = self.env['account.move'].create(invoice_vals)
            created_invoices |= invoice

            # Duplikat Attachment dari petty.cash ke account.move
            for petty in records:
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'petty.cash'),
                    ('res_id', '=', petty.id)
                ])
                
                for attachment in attachments:
                    # Copy attachment dengan res_model dan res_id baru
                    attachment.copy({
                        'name': attachment.name,
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                        'res_name': invoice.name or invoice.display_name,
                    })
                    
            _logger.info("Duplicated %d attachments from petty cash to invoice %s", 
                        len(attachments), invoice.name)

        return self.action_view_invoice(created_invoices)
    
    def _prepare_invoice(self):
        vals = {
            # 'partner_id': self.partner_id.id,
            # 'date': self.date,
            'company_id': self.company_id.id,
            'state': 'draft',
            'move_type': 'in_invoice',
            'invoice_line_ids': self._prepare_invoice_line(),
        }
        return vals
    
    def _prepare_invoice_line(self):
        vals = []
        for line in self:
            vals.append((0,0,{
                'name': line.note or line.product_id.display_name,
                'quantity': line.qty,
                'price_unit': line.price_unit,
                'currency_id': line.currency_id.id,
                'petty_cash_id': line.id,
                'product_id': line.product_id.id,
                'product_uom_id': line.uom_id.id,
            }))
        return vals

    @api.depends('move_line_ids', 'move_line_ids.parent_state')
    def _compute_claimed_status(self):
        for rec in self:
            if rec.petty_cash_type == 'usage':
                # Cari bill yang statusnya bukan 'cancel'
                valid_bills = rec.move_line_ids.filtered(lambda line: line.parent_state != 'cancel')
                
                if valid_bills:
                    rec.is_claimed = 'claimed'
                else:
                    rec.is_claimed = 'not_claimed'
            else:
                rec.is_claimed = 'not_claimed'

    def action_set_claimed(self):
        for rec in self:
            if rec.petty_cash_type == 'usage':
                rec.is_claimed = 'claimed'

    def action_set_not_claimed(self):
        for rec in self:
            if rec.petty_cash_type == 'usage':
                rec.is_claimed = 'not_claimed'

    @api.depends('move_line_ids.analytic_distribution')
    def _compute_analytic_distribution(self):
        for rec in self:
            # Ambil analytic_distribution dari move_line pertama (atau logic lain sesuai kebutuhan)
            analytic = False
            for line in rec.move_line_ids:
                if line.analytic_distribution:
                    analytic = line.analytic_distribution
                    break
            rec.analytic_distribution = analytic or {}


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        for vals, attachment in zip(vals_list, attachments):
            if isinstance(vals, dict) and vals.get('res_model') == 'petty.cash' and vals.get('res_id'):
                petty_cash = self.env['petty.cash'].browse(vals['res_id'])
                bills = petty_cash.move_line_ids.mapped('move_id')
                for bill in bills:
                    attachment.copy({
                        'name': attachment.name,
                        'res_model': 'account.move',
                        'res_id': bill.id,
                        'res_name': bill.name or bill.display_name,
                    })
        return attachments