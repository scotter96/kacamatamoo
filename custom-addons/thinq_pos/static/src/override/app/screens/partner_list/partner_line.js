/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { unaccent } from "@web/core/utils/strings";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";


PartnerLine.props = [
    ...PartnerLine.props,
    "onClickSetAsCustomer",
];


patch(PartnerLine.prototype, {

    // @override
    setup() {
        super.setup(...arguments);
    },

});
