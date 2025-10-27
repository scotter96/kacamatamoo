/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ResPartner } from "@point_of_sale/app/models/res_partner";

patch(ResPartner.prototype, {

    get searchString() {
        const fields = [
            "name",
            "barcode",
            "parent_name",
            "phone",
            "mobile",
            "email",
            "city",
            "birthday",
        ];
        return fields
            .map((field) => {
                if ((field === "phone" || field === "mobile") && this[field]) {
                    return this[field].replace(/[+\s()-]/g, "");
                }
                return this[field] || "";
            })
            .filter(Boolean)
            .join(" ");
    },

    exactMatch(searchWord) {
        const fields = ["barcode", "birthday"];
        return fields.some((field) => this[field] && this[field].toLowerCase() === searchWord);
    }

});
