import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { useService } from "@web/core/utils/hooks";
import { formatCurrency } from '@point_of_sale/app/models/utils/currency';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(ReceiptScreen.prototype, {

    // @override
    async setup() {
        super.setup(...arguments);

        this.pos = usePos();
        this.orm = useService("orm");

        let self = this;
    },

    doPrintInvoice() {
        return this.pos.doPrintInvoice(this.currentOrder.pos_reference);
    },

    orderDone() {
        super.orderDone()
        if (this.pos.config.module_pos_hr) {
            this.pos.showLoginScreen();
        }
    },

    async sendWhatsappMessage() {
        const order = this.currentOrder;
        const partner = order.get_partner();

        if (!partner || !partner.phone) {

            this.dialog.add(
                ConfirmationDialog,
                {
                    title: "Missing Number",
                    message: "This customer has no phone number.",
                    type: "warning",
                }
            );
            return;
        }

        let phone = partner.phone.replace("+", "").trim();
        if (phone.startsWith("0")) {
            phone = "62" + phone.substring(1);
        }

        const total = formatCurrency(order.get_total_with_tax(), order.currency_id.id);
        const downloadAction = await this.pos.data.call(
            "pos.order",
            "action_invoice_download_pdf",
            [this.currentOrder.pos_reference]
        )
        const actionUrl = `${window.location.origin}${downloadAction.url}`
        const shortenerUrl = await this.pos.data.call(
            "url.shortener",
            "generate_short_url",
            [actionUrl]
        )
        const message = `Halo ${partner.name || ''}, terima kasih telah berbelanja di ${this.pos.company.name}!\n\n` +
            `Total pembayaran Anda: ${total}\n` +
            `\nLihat invoice Anda di sini: ${shortenerUrl}\n\n` +
            `Semoga hari Anda menyenangkan!`;

        const waUrl = `https://api.whatsapp.com/send?phone=${phone}&text=${encodeURIComponent(message)}`;
        return window.open(waUrl, "_blank");
    }

});
