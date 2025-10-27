import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {

    async clickRewards() {
        if ( ! this.pos.get_order().get_partner()) {
            alert('Please select a Partner');
            await this.pos.selectPartner();
            return;
        }

        const rewards = this.getPotentialRewards();
        if (rewards.length >= 1) {
            let rewardsList = [];
            for (const key in rewards) {
                var reward = rewards[key];
                console.log(reward);
                if (reward.reward.has_birthday_reward) {
                    if (this.partnerBirthdayValid()) {
                        rewardsList.push({
                            id: reward.reward.id,
                            label: reward.reward.program_id.name,
                            description: `Add "${reward.reward.description}"`,
                            item: reward,
                        });
                    }
                } else {
                    rewardsList.push({
                        id: reward.reward.id,
                        label: reward.reward.program_id.name,
                        description: `Add "${reward.reward.description}"`,
                        item: reward,
                    });
                }
            }

            this.dialog.add(SelectionPopup, {
                title: _t("Available rewards"),
                list: rewardsList,
                getPayload: (selectedReward) => {
                    this._applyReward(
                        selectedReward.reward,
                        selectedReward.coupon_id,
                        selectedReward.potentialQty
                    );
                },
            });
        }
    },

    partnerBirthdayValid() {
        let partner = this.pos.get_order().get_partner();
        if (partner.birthday) {
            return this.isBirthdayWithin7Days(partner.birthday);
        }
        return false;
    },

    isBirthdayWithin7Days(birthdayStr) {
        const today = new Date();
        const currentYear = today.getFullYear();
        const [year, month, day] = birthdayStr.split('-').map(Number);
        let birthday = new Date(currentYear, month - 1, day);

        let diffDays = Math.floor((today - birthday) / (1000 * 60 * 60 * 24));

        if (diffDays <= 7 && diffDays >= 0) {
            return true;
        }
        return false;
    },

});
