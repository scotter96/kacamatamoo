/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { useService, useBus } from "@web/core/utils/hooks";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";


patch(OrderSummary.prototype, {

    // @override
    _setValue(val) {
        super._setValue(val);
        if (val == "remove") {
            this.pos.bus.trigger('DISPLAY-PROMOTIONS');
        }
    }

});
