/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { onMounted, useState } from "@odoo/owl";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";


patch(ProductScreen.prototype, {

    async setup() {
        super.setup(...arguments);
        let self = this;
        // untuk mengambil bus dari POS
        self.bus = self.pos && self.pos.bus ? self.pos.bus : (self.pos ? self.pos.bus = {} : {});
        this.onMounted = onMounted(async function () {
            // Pastikan bus sudah ada sebelum trigger
            if (self.bus && typeof self.bus.trigger === 'function') {
                self.bus.trigger('DISPLAY-PROMOTIONS');
            }
        });
    },

    getProductName(product) {
        // override
        var productName = product.display_name;
        if (product.default_code) {
            productName = "[" + product.default_code + "] " + productName;
        }
        return productName;
    },

});
