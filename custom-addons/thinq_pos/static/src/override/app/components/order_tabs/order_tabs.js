import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { patch } from "@web/core/utils/patch";

patch(OrderTabs.prototype, {
    selectFloatingOrder(order) {
        const data = super.selectFloatingOrder(order);
        this.pos.bus.trigger('DISPLAY-PROMOTIONS');
        return data
    }
})