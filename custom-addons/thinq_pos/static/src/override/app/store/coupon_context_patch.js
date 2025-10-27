/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

// Untuk mengirim data total_qty dan amount_total dari frontend POS ke backend (Odoo)
patch(PosStore.prototype, {
    setup() {
        super.setup(...arguments);
        // intercept call ke backend
        if (!this.data._couponContextPatched) {
            const originalCall = this.data.call.bind(this.data);
            this.data.call = async (model, method, args, kwargs) => {
                // Inject context for coupon
                if (
                    // Jika model yang dipanggil adalah 'pos.config' dan method-nya 'use_coupon_code', maka patch akan berjalan
                    (model === 'pos.config' && method === 'use_coupon_code')
                ) {
                    // Ambil order yang aktif
                    const order = this.get_order();
                    let totalQty = 0; 
                    let amountTotal = 0;

                    // Gunakan method get_orderlines() dan get_total_with_tax()
                    if (order && typeof order.get_orderlines === 'function') {
                        // Gunakan get_orderlines() untuk quantity
                        const lines = order.get_orderlines();
                        totalQty = lines.reduce((sum, line) => sum + (line.qty || 0), 0);
                        // Gunakan get_total_with_tax() untuk amount
                        if (typeof order.get_total_with_tax === 'function') {
                            amountTotal = order.get_total_with_tax();
                        } else if ('amount_total' in order) {
                            amountTotal = order.amount_total;
                        }
                    } else {
                        console.warn("order.get_orderlines() not found, sending 0 values to backend");
                    }

                    // Ambil currency symbol dari POS config
                    let currencySymbol = '';
                    if (this.env.pos && this.env.pos.currency) {
                        currencySymbol = this.env.pos.currency.symbol || '';
                    } else if (this.pos && this.pos.currency) {
                        currencySymbol = this.pos.currency.symbol || '';
                    }
                    if (!currencySymbol) {
                        currencySymbol = 'Rp';
                    }
                    // Inject ke context
                    kwargs = kwargs || {};
                    kwargs.context = kwargs.context || {};
                    kwargs.context.total_qty = totalQty;
                    kwargs.context.amount_total = amountTotal;
                    kwargs.context.currency_symbol = currencySymbol;

                    // Call backend
                    try {
                        const result = await originalCall(model, method, args, kwargs);

                        // Langsung tampilkan pop up hijau
                        showPromoSuccessPopup();

                        return result;
                    } catch (error) {
                        // Error akan ditangani oleh POS (pop up error default)
                        throw error;
                    }
                }
                return await originalCall(model, method, args, kwargs);
            };
            this.data._couponContextPatched = true;
        }
    }
});

// Custom pop up function
function showPromoSuccessPopup() {
    // elemen pop up
    const popup = document.createElement("div");
    popup.style.position = "fixed";
    popup.style.top = "40%";
    popup.style.left = "50%";
    popup.style.transform = "translate(-50%, -50%)";
    popup.style.background = "#fff";
    popup.style.border = "2px solid #4caf50";
    popup.style.borderRadius = "12px";
    popup.style.boxShadow = "0 2px 16px rgba(0,0,0,0.2)";
    popup.style.padding = "32px 48px";
    popup.style.zIndex = "9999";
    popup.style.fontSize = "1.5rem";
    popup.style.color = "#4caf50";
    popup.style.textAlign = "center";
    popup.innerText = "Promo Berhasil dipasang!";

    document.body.appendChild(popup);

    // Auto close after 2 seconds
    setTimeout(() => {
        popup.remove();
    }, 2000);
}
