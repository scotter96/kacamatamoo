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


export class ReturnButton extends Component {
    static template = "thinq_pos.ReturnButton";
    static props = {
        icon: { type: String, optional: true },
        label: { type: String, optional: true },
        class: { type: String, optional: true },
    };
    static defaultProps = {
        label: _t("Return"),
        class: "pos-return-button",
        icon: "fa fa-arrow-circle-right",
    };

    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.state = useState({
            currentReturnId: 0
        });
    }

    async onClick() {
        let self = this;
        const returnId = await this.showReturnList();

        if (returnId > 0) {
            this.state.currentReturnId = returnId;
            const returnForm = await this.showReturnForm();
        }
    }

    async showReturnList() {
        let self = this;
        return await new Promise(async (resolve) => {
            await self.pos.action.doAction("thinq_pos.action_pos_return_list", {
                props: {
                    showButtons: false,
                    allowSelectors: true,
                    onSelectionChanged: async (record) => {
                        if (record && record.length > 0) {
                            resolve(record[0]);
                        }
                    }
                }
            });

        });
    }

    async showReturnForm() {
        let self = this;
        return await new Promise(async (resolve) => {
            await self.pos.action.doAction("thinq_pos.action_pos_return_form", {
                additionalContext: {},
                props: {
                    resId: self.state.currentReturnId,
                    onSave: async (record) => {
                        await self.pos.action.doAction({
                            type: "ir.actions.act_window_close",
                        });
                        resolve(record);
                    },
                },
            });
        });
    }

}

