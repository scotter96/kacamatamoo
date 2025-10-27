import { patch } from "@web/core/utils/patch";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";

patch(InvoiceButton.prototype, {
    async _downloadInvoice(orderId) {
        return this.pos.doPrintInvoice(this.props.order.pos_reference);
    }
})