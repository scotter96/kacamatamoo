/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { unaccent } from "@web/core/utils/strings";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";


patch(PartnerList.prototype, {

    // @override
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.pos = usePos();
    },

    // @override
    async getNewPartners() {
        let domain = [];
        const limit = 30;
        if (this.state.query) {
            const search_fields = [
                "name",
                "parent_name",
                ...this.getPhoneSearchTerms(),
                "email",
                "city",
                "birthday",
                "barcode",
            ];
            domain = [
                ...Array(search_fields.length - 1).fill("|"),
                ...search_fields.map((field) => [field, "ilike", this.state.query + "%"]),
            ];
        }

        const result = await this.pos.data.searchRead("res.partner", domain, [], {
            limit: limit,
            offset: this.state.currentOffset,
        });

        return result;
    },

    // @override
    getPartners() {
        const searchWord = unaccent((this.state.query || "").trim(), false).toLowerCase();

        const partners = this.pos.models["res.partner"].getAll().filter((p) => p.is_customer_store);;
        const exactMatches = partners.filter((partner) => partner.exactMatch(searchWord));

        if (exactMatches.length > 0) {
            return exactMatches;
        }
        const numberString = searchWord.replace(/[+\s()-]/g, "");
        const isSearchWordNumber = /^[0-9]+$/.test(numberString);

        const availablePartners = searchWord
            ? partners.filter((p) =>
                  unaccent(p.searchString).includes(isSearchWordNumber ? numberString : searchWord)
              )
            : partners
                  .filter((p) => p.is_customer_store)
                  .slice(0, 1000)
                  .toSorted((a, b) =>
                      this.props.partner?.id === a.id
                          ? -1
                          : this.props.partner?.id === b.id
                          ? 1
                          : (a.name || "").localeCompare(b.name || "")
                  );

        return availablePartners;
    },

    async setAsCustomer(partner) {
        const update_partner = await this.orm.call('res.partner', "set_as_customer", [
            partner.id
        ]);

        const edited_partner = await this.pos.editPartner(partner);

        this.props.getPayload(partner);
        this.props.close();
    },

});
