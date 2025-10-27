from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order_line(po, item)
        if item.line_id.request_id.date_planned:
            res['date_planned'] = item.line_id.request_id.date_planned
        return res

    @api.model
    def _prepare_item(self, line):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_item(line)
        res['product_qty'] = line.product_qty - line.purchased_qty
        return res

    def make_purchase_order(self):
        messages = []
        for line in self.item_ids:
            remaining_qty = line.line_id.product_qty - line.line_id.purchased_qty
            if line.product_qty > remaining_qty:
                product_name = line.product_id.display_name or line.product_id.name
                messages.append(
                    f"{product_name}: Requested quantity {line.line_id.product_qty} - Already purchased {line.line_id.purchased_qty} = Remaining {remaining_qty}"
                )
        if messages:
            raise ValidationError(
                _("The following quantities exceed the remaining request quantity:\n%s") % "\n".join(messages)
            )
        return super(PurchaseRequestLineMakePurchaseOrder, self).make_purchase_order()