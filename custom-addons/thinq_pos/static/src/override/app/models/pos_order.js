import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { roundDecimals, roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";
import { compute_price_force_price_include } from "@point_of_sale/app/models/utils/tax_utils";
const { DateTime } = luxon;


patch(PosOrder.prototype, {

    partnerBirthdayValid() {
        let partner = this.get_partner();
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

    _applyReward(reward, coupon_id, args) {
        if (reward?.has_birthday_reward) {
            const partner = this.get_partner();
            const valid =
                partner &&
                typeof this.partnerBirthdayValid === "function" &&
                this.partnerBirthdayValid();

            if (!valid) {
                return false;
            }
        }
        return super._applyReward(reward, coupon_id, args);
    },

    _getRealCouponPoints(coupon_id) {
        let points = 0;
        const dbCoupon = this.models["loyalty.card"].get(coupon_id);
        if (dbCoupon) {
            points += dbCoupon.points;
        }
        Object.values(this.uiState.couponPointChanges).some((pe) => {
            if (pe.coupon_id === coupon_id) {
                if (this.models["loyalty.program"].get(pe.program_id).applies_on !== "future") {
                    points += pe.points;
                }
                // couponPointChanges is not supposed to have a coupon multiple times
                return true;
            }
            return false;
        });
        for (const line of this.get_orderlines()) {
            // Temporary Fixing error bawaan
            if (line.is_reward_line && line.coupon_id?.id === coupon_id) {
                points -= line.points_cost;
            }
        }
        return points;
    },

    // OVERRIDE
    _getDiscountableOnCheapest(reward) {
        const applicableProductIds = new Set(
            (reward.all_discount_product_ids || []).map((p) => p.id)
        );

        let orderLines = this.get_orderlines();

        if (applicableProductIds.size > 0) {
            orderLines = orderLines.filter((line) =>
                applicableProductIds.has(line.product_id.id)
            );
        }

        if (!orderLines.length) {
            return { discountable: 0, discountablePerTax: {} };
        }

        const cheapestLine = orderLines.reduce((minLine, line) => {
            return line.getComboTotalPriceWithoutTax() <
                minLine.getComboTotalPriceWithoutTax()
                ? line
                : minLine;
        });

        const taxKey = cheapestLine.tax_ids.map((t) => t.id);
        const amount = cheapestLine.getComboTotalPriceWithoutTax();

        return {
            discountable: amount,
            discountablePerTax: { [taxKey]: amount },
        };
    }


});
