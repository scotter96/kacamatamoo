# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from markupsafe import Markup

from odoo import _, api, exceptions, fields, models
from odoo.tools import html_escape
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _purchase_request_confirm_message_content(self, request, request_dict=None):
        self.ensure_one()
        if not request_dict:
            request_dict = {}
        title = _("Order confirmation %(po_name)s for your Request %(pr_name)s") % {
            "po_name": self.name,
            "pr_name": request.name,
        }
        message = f"<h3>{title}</h3><ul>"
        message += _(
            "The following requested items from Purchase Request %(pr_name)s "
            "have now been confirmed in Purchase Order %(po_name)s:",
            po_name=self.name,
            pr_name=request.name,
        )

        for line in request_dict.values():
            message += _(
                "<li><b>%(prl_name)s</b>: Ordered quantity %(prl_qty)s %(prl_uom)s, "
                "Planned date %(prl_date_planned)s</li>"
            ) % {
                "prl_name": html_escape(line["name"]),
                "prl_qty": line["product_qty"],
                "prl_uom": line["product_uom"],
                "prl_date_planned": line["date_planned"],
            }
        message += "</ul>"
        return message

    def _purchase_request_confirm_message(self):
        request_obj = self.env["purchase.request"]
        for po in self:
            requests_dict = {}
            for line in po.order_line:
                for request_line in line.sudo().purchase_request_lines:
                    request_id = request_line.request_id.id
                    if request_id not in requests_dict:
                        requests_dict[request_id] = {}
                    date_planned = line.date_planned
                    data = {
                        "name": request_line.name,
                        "product_qty": line.product_qty,
                        "product_uom": line.product_uom.name,
                        "date_planned": date_planned,
                    }
                    requests_dict[request_id][request_line.id] = data
            for request_id in requests_dict:
                request = request_obj.sudo().browse(request_id)
                message = po._purchase_request_confirm_message_content(
                    request, requests_dict[request_id]
                )
                request.message_post(
                    body=Markup(message),
                    subtype_id=self.env.ref(
                        "purchase_request.mt_request_po_confirmed"
                    ).id,
                )
        return True

    def _purchase_request_line_check(self):
        for po in self:
            for line in po.order_line:
                for request_line in line.purchase_request_lines:
                    if request_line.sudo().purchase_state == "done":
                        raise exceptions.UserError(
                            _("Purchase Request %s has already been completed")
                            % (request_line.request_id.name)
                        )
        return True

    def button_confirm(self):
        self._purchase_request_line_check()
        res = super().button_confirm()
        self._purchase_request_confirm_message()
        return res

    def unlink(self):
        alloc_to_unlink = self.env["purchase.request.allocation"]
        for rec in self:
            for alloc in (
                rec.order_line.mapped("purchase_request_lines")
                .mapped("purchase_request_allocation_ids")
                .filtered(
                    lambda alloc, rec=rec: alloc.purchase_line_id.order_id.id == rec.id
                )
            ):
                alloc_to_unlink += alloc
        res = super().unlink()
        alloc_to_unlink.unlink()
        return res
    
    def button_draft(self):
        """Override button_draft to validate PR quantities when reactivating cancelled PO"""
        _logger.info("=== PO BUTTON_DRAFT METHOD CALLED ===")
        
        # Validate each PO line before changing state to draft
        for order in self:
            if order.state == 'cancel':
                _logger.info(f"Validating cancelled PO: {order.name}")
                order._validate_pr_qty_on_reactivate()
        
        # Proceed with original button_draft
        return super().button_draft()

    def _validate_pr_qty_on_reactivate(self):
        """
        Validate that reactivating this cancelled PO won't exceed PR quantities
        """
        _logger.info(f"=== VALIDATE_PR_QTY_ON_REACTIVATE for PO: {self.name} ===")
        
        for po_line in self.order_line:
            # Get related Purchase Request Lines
            pr_lines = po_line.purchase_request_lines
            
            if not pr_lines:
                continue
                
            for pr_line in pr_lines:
                _logger.info(f"Checking PR Line: {pr_line.id} - Product: {pr_line.product_id.name}")
                
                # Get current purchased_qty (without this cancelled PO)
                current_purchased_qty = pr_line.purchased_qty
                _logger.info(f"Current purchased_qty: {current_purchased_qty}")
                
                # Convert PO line qty to PR line UOM if different
                if pr_line.product_uom_id and po_line.product_uom != pr_line.product_uom_id:
                    po_line_qty_converted = po_line.product_uom._compute_quantity(
                        po_line.product_qty, pr_line.product_uom_id
                    )
                else:
                    po_line_qty_converted = po_line.product_qty
                
                _logger.info(f"PO line qty (converted): {po_line_qty_converted}")
                
                # Calculate total if this PO is reactivated
                total_qty_if_reactivated = current_purchased_qty + po_line_qty_converted
                _logger.info(f"Total qty if reactivated: {total_qty_if_reactivated}")
                _logger.info(f"PR qty limit: {pr_line.product_qty}")
                
                # Check if total would exceed PR qty
                if total_qty_if_reactivated > pr_line.product_qty:
                    # Get details of other active POs for this PR line
                    other_active_pos = []
                    for other_po_line in pr_line.purchase_lines.filtered(lambda x: x.state != 'cancel'):
                        if other_po_line.id != po_line.id:
                            if pr_line.product_uom_id and other_po_line.product_uom != pr_line.product_uom_id:
                                converted_qty = other_po_line.product_uom._compute_quantity(
                                    other_po_line.product_qty, pr_line.product_uom_id
                                )
                            else:
                                converted_qty = other_po_line.product_qty
                            other_active_pos.append(f"• {other_po_line.order_id.name}: {converted_qty:.2f}")
                    
                    raise ValidationError(_(
                        "🚫 VALIDATION ERROR: Cannot Set Purchase Order to Draft!\n\n"
                        "📋 PURCHASE REQUEST QUANTITY VALIDATION FAILED:\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "🔸 Purchase Order: %(po_name)s\n"
                        "🔸 Product: %(product_name)s\n\n"
                        "📊 QUANTITY ANALYSIS:\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "🎯 Purchase Request Quantity (PR): %(pr_qty).2f %(uom)s\n"
                        "✅ Current Purchased Quantity: %(current_purchased_qty).2f %(uom)s\n"
                        "⚡ This PO Line Quantity: %(this_po_qty).2f %(uom)s\n"
                        "📦 TOTAL if Reactivated: %(total_if_reactivated).2f %(uom)s\n\n"
                        "⚠️ PROBLEM DETECTED:\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "If this Purchase Order is reactivated, the total purchased quantity\n"
                        "(%(total_if_reactivated).2f) will EXCEED the Purchase Request quantity (%(pr_qty).2f).\n\n"
                        "This means you would be purchasing more than what was originally requested!"
                    ) % {
                        'po_name': self.name,
                        'product_name': pr_line.product_id.name or 'N/A',
                        'po_qty': po_line.product_qty,
                        'pr_qty': pr_line.product_qty,
                        'current_purchased_qty': current_purchased_qty,
                        'this_po_qty': po_line_qty_converted,
                        'total_if_reactivated': total_qty_if_reactivated,
                        'uom': pr_line.product_uom_id.name or '',
                        'other_active_pos': '\n'.join(other_active_pos) if other_active_pos else 'None',
                        'pr_name': pr_line.request_id.name or 'N/A',
                    })
                    
        _logger.info("All PR quantity validations passed for PO reactivation")


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    purchase_request_lines = fields.Many2many(
        comodel_name="purchase.request.line",
        relation="purchase_request_purchase_order_line_rel",
        column1="purchase_order_line_id",
        column2="purchase_request_line_id",
        readonly=True,
        copy=False,
    )

    purchase_request_allocation_ids = fields.One2many(
        comodel_name="purchase.request.allocation",
        inverse_name="purchase_line_id",
        string="Purchase Request Allocation",
        copy=False,
    )

    def action_open_request_line_tree_view(self):
        """
        :return dict: dictionary value for created view
        """
        request_line_ids = []
        for line in self:
            request_line_ids += line.purchase_request_lines.ids

        domain = [("id", "in", request_line_ids)]

        return {
            "name": _("Purchase Request Lines"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.request.line",
            "view_mode": "list,form",
            "domain": domain,
        }

    def _prepare_stock_moves(self, picking):
        self.ensure_one()
        val = super()._prepare_stock_moves(picking)
        all_list = []
        for v in val:
            all_ids = self.env["purchase.request.allocation"].search(
                [("purchase_line_id", "=", v["purchase_line_id"])]
            )
            for all_id in all_ids:
                all_list.append((4, all_id.id))
            v["purchase_request_allocation_ids"] = all_list
        return val

    def update_service_allocations(self, prev_qty_received):
        for rec in self:
            allocation = self.env["purchase.request.allocation"].search(
                [
                    ("purchase_line_id", "=", rec.id),
                    ("purchase_line_id.product_id.type", "=", "service"),
                ]
            )
            if not allocation:
                return
            qty_left = rec.qty_received - prev_qty_received
            for alloc in allocation:
                allocated_product_qty = alloc.allocated_product_qty
                if not qty_left:
                    alloc.purchase_request_line_id._compute_qty()
                    break
                if alloc.open_product_qty <= qty_left:
                    allocated_product_qty += alloc.open_product_qty
                    qty_left -= alloc.open_product_qty
                    alloc._notify_allocation(alloc.open_product_qty)
                else:
                    allocated_product_qty += qty_left
                    alloc._notify_allocation(qty_left)
                    qty_left = 0
                alloc.write({"allocated_product_qty": allocated_product_qty})

                message_data = self._prepare_request_message_data(
                    alloc, alloc.purchase_request_line_id, allocated_product_qty
                )
                message = self._purchase_request_confirm_done_message_content(
                    message_data
                )
                alloc.purchase_request_line_id.request_id.message_post(
                    body=Markup(message),
                    subtype_id=self.env.ref("mail.mt_note").id,
                )

                alloc.purchase_request_line_id._compute_qty()
        return True

    @api.model
    def _purchase_request_confirm_done_message_content(self, message_data):
        title = _("Service confirmation for Request {request_name}").format(
            request_name=message_data["request_name"]
        )

        message_body = _(
            "The following requested services from Purchase Request {request_name} "
            "requested by {requestor} have now been received:"
        ).format(
            request_name=message_data["request_name"],
            requestor=message_data["requestor"],
        )

        product_line = Markup(
            "<ul><li><b>{}</b>: " + _("Received quantity") + " {} {}</li></ul>"
        ).format(
            html_escape(message_data["product_name"]),
            message_data["product_qty"],
            html_escape(message_data["product_uom"]),
        )

        return Markup("<h3>{}</h3>{}{}").format(title, message_body, product_line)

    def _prepare_request_message_data(self, alloc, request_line, allocated_qty):
        return {
            "request_name": request_line.request_id.name,
            "product_name": request_line.product_id.display_name,
            "product_qty": allocated_qty,
            "product_uom": alloc.product_uom_id.name,
            "requestor": request_line.request_id.requested_by.partner_id.name,
        }

    def write(self, vals):
        #  As services do not generate stock move this tweak is required
        #  to allocate them.
        prev_qty_received = {}
        if vals.get("qty_received", False):
            service_lines = self.filtered(
                lambda line: line.product_id.type == "service"
            )
            for line in service_lines:
                prev_qty_received[line.id] = line.qty_received
        res = super().write(vals)
        if prev_qty_received:
            for line in service_lines:
                line.update_service_allocations(prev_qty_received[line.id])
        return res
