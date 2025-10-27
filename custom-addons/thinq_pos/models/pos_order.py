from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

PICKED_UP_STATES = [
    ('draft', 'Not Picked Up'),
    ('partially', 'Partially Picked Up'),
    ('done', 'Picked Up')
]

class PosOrder(models.Model):
    _inherit = 'pos.order'

    refraction_line_ids = fields.One2many(
        'pos.order.refraction',
        'pos_order_id',
        string='Lens Prescriptions',
        help="List of lens prescriptions for this order"
    )

    picked_up_state = fields.Selection(PICKED_UP_STATES, copy=False, compute='_compute_picked_up_state', store=True)

    def _generate_pos_order_invoice(self):
        self = self.with_context(generate_pdf=False)
        res = super(PosOrder, self)._generate_pos_order_invoice()
        return res

    def format_currency(self, amount):
        """Format angka dengan simbol mata uang dari currency, tanpa desimal"""
        if not amount and amount != 0:
            amount = 0

        currency = self.currency_id

        formatted_amount = "{:,.0f}".format(amount).replace(",", ".")

        if currency.position == "before":
            return f"{currency.symbol} {formatted_amount}"
        else:
            return f"{formatted_amount} {currency.symbol}"
    
    def picked_up_all(self):
        for line in self.lines.filtered(lambda x:not x.picked_up):
            line.picked_up = True
            line._onchange_picked_up()

    @api.depends('lines.picked_up')
    def _compute_picked_up_state(self):
        for rec in self:
            state = 'draft'
            product_lines = rec.lines.filtered(lambda x:x.product_id.type != 'service')
            if all(l.picked_up for l in product_lines):
                state = 'done'
            elif all(not l.picked_up for l in product_lines):
                state = 'draft'
            elif any(not l.picked_up for l in product_lines):
                state = 'partially'
            rec.picked_up_state = state

    # >>>>>>>>>> Coupon Validation Functions >>>>>>>>>>

    # Tujuan: Override proses aplikasi coupon pada order POS.
    def _apply_coupon_code(self, coupon_code):
        """Override to validate coupon before applying"""
        
        # - Mengambil semua order lines dari order saat ini (self.lines)
        order_lines = []
        for line in self.lines:
            order_lines.append({
                # - Membuat list berisi dict setiap line: qty, price_unit, product_id
                'qty': line.qty,
                'price_unit': line.price_unit,
                'product_id': line.product_id.id
            })

        # - Memanggil method validate_coupon_conditions di model loyalty.program untuk validasi coupon berdasarkan order lines dan coupon code
        loyalty_program = self.env['loyalty.program']
        validation = loyalty_program.validate_coupon_conditions(order_lines, coupon_code)

        # - Jika validasi gagal (validation['valid'] False), raise UserError dengan pesan error yang relevan
        if not validation['valid']:
            raise UserError(validation['message'])

        # - Jika lolos validasi, lanjutkan proses coupon dengan memanggil super()._apply_coupon_code(coupon_code)
        return super()._apply_coupon_code(coupon_code)


    # Tujuan: Override proses pembuatan order dari data frontend (UI), termasuk validasi coupon
    @api.model  
    def _order_fields(self, ui_order):
        """Override to validate coupon saat order di-process"""
        # - Memanggil method asli Odoo untuk mendapatkan hasil awal
        result = super()._order_fields(ui_order)
        
        # Cek jika ada coupon yang applied
        if ui_order.get('loyalty_points', []):
            # - Mengecek apakah ada coupon yang di-applied pada order (ui_order['loyalty_points'])
            for loyalty_point in ui_order['loyalty_points']:
                if loyalty_point.get('code'):
                    # - Untuk setiap coupon, ambil kode coupon dan hitung total_qty serta total_amount dari data order
                    coupon_code = loyalty_point['code']
                    
                    # Get order totals from UI order
                    total_qty = sum(line[2]['qty'] for line in ui_order['lines'] if len(line) >= 3)
                    total_amount = ui_order.get('amount_total', 0)
                    
                    # - Memanggil _validate_coupon_with_totals untuk validasi coupon dengan data qty dan amount
                    validation = self._validate_coupon_with_totals(coupon_code, total_qty, total_amount)
                    
                    # - Jika validasi gagal, raise UserError dengan pesan error
                    if not validation['valid']:
                        raise UserError(validation['message'])
                    
        # - Jika lolos, lanjutkan proses order
        return result
    
    # Tujuan: Validasi coupon berdasarkan total qty dan amount yang sudah diketahui.
    def _validate_coupon_with_totals(self, coupon_code, total_qty, total_amount):
        """Validate coupon dengan total yang sudah diketahui"""
        loyalty_program = self.env['loyalty.program']
        
        # - Cari coupon dan program berdasarkan kode coupon
        coupon = self.env['loyalty.card'].search([('code', '=', coupon_code)], limit=1)
        # - Jika tidak ditemukan, return validasi gagal
        if not coupon:
            return {'valid': False, 'message': 'Invalid coupon code'}
        
        program = coupon.program_id
        if not program:
            return {'valid': False, 'message': 'Invalid coupon program'}

        # Get rules with conditions -> minimum_qty and minimum_amount
        conditional_rules = program.rule_ids.filtered(lambda r: r.minimum_qty > 0 or r.minimum_amount > 0)
        
        # - Jika tidak ada rules, coupon dianggap valid
        if not conditional_rules:
            return {'valid': True, 'message': ''}
        
        # - Jika ada, cek apakah total_qty dan total_amount memenuhi syarat
        rule = conditional_rules[0]
        validation_errors = []

        # - Jika tidak memenuhi, return validasi gagal beserta pesan error
        # Check minimum quantity
        if rule.minimum_qty and total_qty < rule.minimum_qty:
            validation_errors.append(f"Minimum {rule.minimum_qty} items required. Current: {int(total_qty)}")

        # Check minimum amount
        if rule.minimum_amount and total_amount < rule.minimum_amount:
            validation_errors.append(f"Minimum purchase ${rule.minimum_amount:.2f} required. Current: ${total_amount:.2f}")

        if validation_errors:
            return {
                'valid': False,
                'message': 'Coupon cannot be applied:\n' + '\n'.join(validation_errors)
            }

         # - Jika memenuhi, return validasi sukses
        return {'valid': True, 'message': ''}
    
    # Catatan:
    # Fungsi-fungsi di pos_order.py yang berhubungan dengan coupon (seperti _apply_coupon_code, _order_fields, dan _validate_coupon_with_totals)
    # hanya diperlukan jika ingin validasi ulang saat order diproses/simpan (double check di backend) atau menjaga integritas data jika ada order
    # yang masuk dari luar POS (misal import, API, dsb).
    # Validasi utama sudah di-handle di pos_config.py.

    @api.model
    def action_invoice_download_pdf(self, order_ref):
        order_id = self.sudo().search([
                ('pos_reference', '=', order_ref)
            ], limit=1, order='id desc')
        return {
            'type': 'ir.actions.act_url',
            'url': '/thinq_pos/report/pos_order/invoice/%s' % order_id.id,
            'target': 'download',
        }

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    picked_up = fields.Boolean(
        string='Picked Up',
        default=False,
        help="Check if the product has been picked up by the customer",
        copy=False
    )

    picked_date = fields.Datetime('Picked On', copy=False)

    @api.onchange('picked_up')
    def _onchange_picked_up(self):
        if self.picked_up:
            self.picked_date = datetime.now()
