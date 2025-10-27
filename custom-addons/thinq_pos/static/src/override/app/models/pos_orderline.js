import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                refraction_created: { type: Boolean, optional: true },
            },
        },
    },
});


patch(PosOrderline.prototype, {

    setup() {
        super.setup(...arguments);
    },

    set_refraction_created(created) {
        this.refraction_created = created ? true : false;
    },

    get_refraction_created() {
        return this.refraction_created ? true : false;
    },

    getDisplayData() {
        let data = super.getDisplayData();
        data['refraction_created'] = this.get_refraction_created();
        return data;
    },

});
