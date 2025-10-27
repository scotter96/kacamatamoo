from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_price_different = fields.Boolean(
        "Price Differs from Pricelist",
        compute="_compute_is_price_different",
        store=True
    )
    confirm_price_approved = fields.Boolean(
        "Approve Price Different",
        default=False,
        help="Checked by Finance or authorized user"
    )

    @api.depends('order_line.product_id', 'order_line.price_unit', 'pricelist_id')
    def _compute_is_price_different(self):
        for order in self:
            mismatch = order._get_price_mismatch_lines()
            order.is_price_different = len(mismatch) > 0

    def _get_price_mismatch_lines(self):
        self.ensure_one()
        if not self.pricelist_id or not self.order_line:
            return []

        mismatch = []
        for line in self.order_line:
            if not line.product_id or line.product_uom_qty <= 0:
                continue

            computed_price = self.pricelist_id._get_product_price(
                product=line.product_id,
                quantity=line.product_uom_qty,
                uom=line.product_uom,
            )
            if abs(computed_price - line.price_unit) > 0.01:
                mismatch.append({
                    'product': line.product_id,
                    'list_price': computed_price,
                    'so_price': line.price_unit,
                })
        return mismatch

    def action_request_price_approval(self):
        self.ensure_one()

        mismatch_lines = self._get_price_mismatch_lines()
        if not mismatch_lines:
            return {
                'warning': {
                    'title': "No Price Override",
                    'message': "All prices match the pricelist. No approval needed.",
                }
            }

        approve_group = self.env.ref('thinq_sale.group_approve_price_different', raise_if_not_found=False)
        if not approve_group or not approve_group.users:
            raise UserError("Approval group not found or has no users.")

        products_text = "\n".join([
            f"{item['product'].display_name}: {item['list_price']:.2f} → {item['so_price']:.2f}"
            for item in mismatch_lines
        ])

        self.message_post(
            body=f"<b>Approval Requested</b><br/>"
                 f"The following items have prices different from the pricelist:<br/><pre>{products_text}</pre><br/>"
                 f"Requested by: <b>{self.env.user.name}</b>",
            subject="Manual Pricing - Approval Request",
            message_type='notification',
            partner_ids=approve_group.users.mapped('partner_id').ids,
        )

        for user in approve_group.users:
            self.env['mail.activity'].create({
                'res_model_id': self.env['ir.model']._get_id('sale.order'),
                'res_id': self.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': 'Review Price Change',
                'note': 'This order contains manually adjusted prices. Please review before approval.',
                'user_id': user.id,
                'automated': True,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Approval Request Sent',
                'message': 'Your request has been sent to the Finance team.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_confirm(self):
        for order in self:
            if order.is_price_different and not order.confirm_price_approved:
                mismatch_lines = order._get_price_mismatch_lines()
                products_list = "\n".join([
                    f"• {item['product'].display_name}: {item['list_price']:.2f} → {item['so_price']:.2f}"
                    for item in mismatch_lines
                ])
                raise UserError(
                    "Cannot confirm this order. Prices differ from pricelist "
                    "and require approval from Finance.\n\n"
                    "Products with manual pricing:\n"
                    + products_list + "\n\n"
                    "Please use 'Request Approval' button and wait for confirmation."
                )
        return super().action_confirm()