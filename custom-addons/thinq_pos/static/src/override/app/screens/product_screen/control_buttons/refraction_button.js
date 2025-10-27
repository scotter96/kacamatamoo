import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { useService } from "@web/core/utils/hooks";
import {
    makeAwaitable,
    ask,
    makeActionAwaitable,
} from "@point_of_sale/app/store/make_awaitable_dialog";
import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";


export class RefractionButton extends Component {
    static template = "thinq_pos.RefractionButton";
    static props = {
        icon: { type: String, optional: true },
        label: { type: String, optional: true },
        class: { type: String, optional: true },
    };
    static defaultProps = {
        label: _t("Refraction"),
        class: "pos-return-button",
        icon: "fa fa-arrow-circle-right",
    };

    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.notification = useService("notification");
    }

    async onClick() {
        await this.showRefractions();
    }

    async showRefractions() {
        if ( ! this.pos.get_order().get_partner()) {
            await this.pos.selectPartner();
            return;
        }

        await this.pos.syncAllOrders({ orders: [this.pos.get_order()] });

        let resp = await this.pos.data.call(
            'pos.order.refraction',
            "show_refractions",
            [this.pos.get_order().pos_reference]);

        let frame_ids = [];

        if (resp) {
            let ids = [];

            for (const k in resp) {
                ids.push(resp[k].id);
            }

            if (ids.length > 0) {
                await this.editRefractions(ids);
            } else {
                await this.noRefractions();
            }
        } else {
            await this.noRefractions();
        }
    }

    async noRefractions() {
        // TODO: Refraction: Need new refraction creation?
        this.notification.add(_t("No refraction data, please click Payment"), { type: "info" });
    }

    async editRefractions(ids) {
        let self = this;
        let frame_ids = [];
        let lines = this.pos.get_order().lines;

        for (const k in lines) {
            var line = lines[k];
            if (line.product_id.is_frame) {
                frame_ids.push(line.product_id.id);
            }
        }

        return await new Promise(async (resolve) => {
            await self.pos.action.doAction("thinq_pos.action_pos_add_refraction_tree", {
                props: {
                    showButtons: true,
                    allowSelectors: true,
                },
                additionalContext: {
                    'search_default_id': ids,
                    'active_ids': ids,
                    'frame_ids': frame_ids,
                }
            });

        });
    }

}

