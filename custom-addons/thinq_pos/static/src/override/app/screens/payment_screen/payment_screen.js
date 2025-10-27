import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from '@point_of_sale/app/screens/payment_screen/payment_screen';
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    shouldDownloadInvoice() {
        return false;
    },

    onMounted() {
        super.onMounted();
        if (!this.currentOrder.is_to_invoice()) {
            this.toggleIsToInvoice();
        }
    }

})