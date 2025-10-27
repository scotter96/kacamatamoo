/** @odoo-module */
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { formatCurrency } from '@point_of_sale/app/models/utils/currency';

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                get_product_bundle_pack_data: { type: Object, optional: true },
            },
        },
    },
});

patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
    },

    get_product_bundle_pack_data() {
        const product = this.get_product();
        if (!product) {
            return [];
        }
        let packs = product.pack_ids.map((pack) => ({
            id: pack.id,
            product_name: pack.name,
            qty_available: pack.qty_available,
            is_storable: pack.is_storable,
            qty_uom: pack.qty_uom * this.get_quantity(),
            uom_id: {
                id: pack.uom_id.id,
                display_name: pack.uom_id.name,
            },
            price: pack.price,
            price_formatted: formatCurrency(pack.price, this.currency),
            subtotal: pack.price * this.get_quantity(),
            subtotal_formatted: formatCurrency(pack.price * this.get_quantity(), this.currency),
        }));
        return packs
    },

    getDisplayData() {
        let data = super.getDisplayData();
        data['get_product_bundle_pack_data'] = this.get_product_bundle_pack_data();
        return data;
    },
});
