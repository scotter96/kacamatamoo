/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { useService, useBus } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


patch(SelectPartnerButton.prototype,  {

    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        this.state = useState({
            promotions: this.pos.displayPromotions()
        });
        let self = this;
        useBus(this.pos.bus, 'DISPLAY-PROMOTIONS', function () {
            self.displayPromotions();
        });
        // useBus(this.pos.bus, 'EDIT-REFRACTIONS-CONFIRMATION', async function () {
        //     return await self.editRefractionsConfirmation();
        // });
    },

    // async editRefractionsConfirmation() {
    //     const doEditRefractions = await new Promise((resolve) => {
    //         this.dialogService.add(ConfirmationDialog, {
    //             body: _t("Edit Refractions?"),
    //                                confirmLabel: _t('Edit'),
    //                                cancelLabel: _t('Skip'),
    //                                cancel: () => resolve(false),
    //                                close: () => resolve(false),
    //                                confirm: () => resolve(true),
    //         });
    //     });
    //     return doEditRefractions;
    // },

    async clickRewards(selectedReward) {
        this._applyReward(
            selectedReward.reward,
            selectedReward.coupon_id,
            selectedReward.potentialQty
        );
    },

    /**
     * Applies the reward on the current order, if multiple products can be claimed opens a popup asking for which one.
     *
     * @param {Object} reward
     * @param {Integer} coupon_id
     */
    async _applyReward(reward, coupon_id, potentialQty) {
        const order = this.pos.get_order();

        if (reward.has_birthday_reward && !this.pos.partnerBirthdayValid()) {
            this.notification.add(
                _t("This reward is only available if your birthday is within the allowed period."),
                { type: "warning" }
            );
            return false;
        }

        order.uiState.disabledRewards.delete(reward.id);

        const args = {};
        if (reward.reward_type === "product" && reward.multi_product) {
            const productsList = reward.reward_product_ids.map((product_id) => ({
                id: product_id.id,
                label: product_id.display_name,
                item: product_id,
            }));
            const selectedProduct = await makeAwaitable(this.pos.dialog, SelectionPopup, {
                title: _t("Please select a product for this reward"),
                list: productsList,
            });
            if (!selectedProduct) {
                return false;
            }
            args["product"] = selectedProduct;
        }
        if (
            (reward.reward_type == "product" && reward.program_id.applies_on !== "both") ||
            (reward.program_id.applies_on == "both" && potentialQty)
        ) {
            await this.pos.addLineToCurrentOrder(
                {
                    product_id: args["product"] || reward.reward_product_ids[0],
                    qty: potentialQty || 1,
                },
                {}
            );
            return true;
        } else {
            const result = order._applyReward(reward, coupon_id, args);
            if (result !== true) {
                // Returned an error
                this.notification.add(result);
            }
            this.pos.updateRewards();
            return result;
        }
    },

    displayPromotions() {
        this.state.promotions = this.pos.displayPromotions();

        for (const reward of this.state.promotions) {
            if (reward.reward.has_birthday_reward && this.pos.partnerBirthdayValid()) {
                const order = this.pos.get_order();
                const alreadyApplied = order
                    .get_orderlines()
                    .some((line) => line.reward_id === reward.reward.id);

                if (!alreadyApplied) {
                    this._applyReward(
                        reward.reward,
                        reward.coupon_id,
                        reward.potentialQty
                    );
                }
            }
        }
    },

});

