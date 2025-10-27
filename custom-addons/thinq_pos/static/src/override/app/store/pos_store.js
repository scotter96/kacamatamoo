/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { makeActionAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {

    // @override
    setup() {
        super.setup(...arguments);
        this.promotions = [];
        this.bus.trigger('DISPLAY-PROMOTIONS');
    },

    async doPrintInvoice(order_ref) {
        const downloadAction = await this.data.call(
            "pos.order",
            "action_invoice_download_pdf",
            [order_ref]
        );
        console.log('DOWNLOAD INV', downloadAction)
        await this.action.doAction(downloadAction);
    },

    async editPartner(partner) {
        const record = await makeActionAwaitable(
            this.action,
            "thinq_pos.thinq_res_partner_action_edit_pos",
            {
                props: { resId: partner?.id },
                additionalContext: this.editPartnerContext(),
            }
        );
        const newPartner = await this.data.read("res.partner", record.config.resIds);
        return newPartner[0];
    },

    // @override
    async pay() {
        let currentOrder = this.get_order();
        if ( ! currentOrder.get_partner()) {
            await this.selectPartner();
        } else if (await this.hasLens()) {
            // await this.editRefractions();
            await this.createRefractions(); // di UPSERT aja biar ganteng
            await super.pay();
        } else {
            await super.pay();
        }
    },

    // @override
    editPartnerContext(partner) {
        let context = super.editPartnerContext(partner);
        context.default_is_customer_store = true;
        return context;
    },

    // // @override
    async selectPartner() {
        let currentPartner = await super.selectPartner();
        this.displayPromotions();
        this.bus.trigger('DISPLAY-PROMOTIONS');
        return currentPartner;
    },

    add_new_order() {
        const order = super.add_new_order(...arguments);
        this.bus.trigger('DISPLAY-PROMOTIONS');
        return order;
    },

    displayPromotions() {
        const currentPartner = this.get_order()?.get_partner();
        if (currentPartner) {
            this.promotions = this.getPotentialRewards();
        } else {
            this.promotions = [];
        }

        return this.promotions;
    },

    getPotentialRewards() {
        const order = this.get_order();
        const partner = order ? order.get_partner() : null;

        let rewards = [];
        if (order) {
            const claimableRewards = order.getClaimableRewards();
            rewards = claimableRewards.filter(
                ({ reward }) => reward.program_id.program_type !== "ewallet"
            );
        }

        const result = {};
        const discountRewards = rewards.filter(({ reward }) => reward.reward_type == "discount");
        const freeProductRewards = rewards.filter(({ reward }) => reward.reward_type == "product");
        const potentialFreeProductRewards = this.getPotentialFreeProductRewards();
        const avaiRewards = [
            ...potentialFreeProductRewards,
            ...discountRewards,
            ...freeProductRewards,
        ];

        // Step 1: kalau tidak ada partner, langsung kosongkan birthday rewards
        if (!partner) {
            // hanya kembalikan reward yang bukan birthday type
            const nonBirthdayRewards = avaiRewards.filter(
                (r) => !r.reward.has_birthday_reward
            );
            return nonBirthdayRewards;
        }

        // Step 2: kalau ada partner, lakukan validasi birthday normal
        for (const reward of avaiRewards) {
            if (reward.reward.has_birthday_reward) {
                if (this.partnerBirthdayValid()) {
                    result[reward.reward.id] = reward;
                }
            } else {
                result[reward.reward.id] = reward;
            }
        }

        return Object.values(result);
    },

    partnerBirthdayValid() {
        let partner = this.get_order().get_partner();
        if (partner.birthday) {
            const partner_birthday = this.isBirthdayWithin7Days(partner.birthday)
            return partner_birthday;
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


    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        await super.addLineToCurrentOrder(vals, opts, configure);
        this.bus.trigger('DISPLAY-PROMOTIONS');
    },

    async hasLens() {
        await this.syncAllOrders({ orders: [this.get_order()] });

        let lines = this.get_order().lines;

        const hasLens = lines.some((line) => line.product_id.is_lens === true);

        return hasLens;
    },

    isAllRefractionCreated() {
        for (const _k in this.get_order().lines) {
            var line = this.get_order().lines[_k];
            if (line.product_id.is_lens) {
                if ( !line.refraction_created) {
                    return false;
                }
            }
        }

        return true;
    },

    async editRefractions() {
        let ids = await this.availableRefractions();

        if (!ids || ids.length == 0) {
            await this.createRefractions();
        } else {
            await this._editRefractions(ids);
        }
    },

    async availableRefractions() {
        return await this.data.call(
            'pos.order.refraction',
            "available_refractions",
            [this.get_order().pos_reference]);
    },

    async createRefractions() {
        let products = this.getLensProducts();

        let resp = await this.data.call(
            'pos.order.refraction',
            "create_refractions",
            [this.get_order().pos_reference, products]);

        if (resp) {
            let ids = [];

            for (const k in resp) {
                ids.push(resp[k].id);
            }

            if (ids.length > 0) {
                await this._editRefractions(ids);
            }
        }
    },

    async _editRefractions(ids) {
        const frame_ids = [];
        const lines = this.get_order().lines;

        for (const line of lines) {
            if (line.product_id.is_frame) {
                frame_ids.push(line.product_id.id);
            }
            if (line.product_id.is_lens) {
                line.set_refraction_created(true);
            }
        }

        return new Promise(async (resolve) => {
            await this.action.doAction("thinq_pos.pos_order_refraction_action", {
                props: {
                    resId: this.get_order().id,
                    onSave: async (record) => {
                        const refraction_lines = await this.data.read('pos.order.refraction', record.evalContext.refraction_line_ids)
                        console.log('REFRACTION LINES', refraction_lines)
                        const mustHaveFrame = frame_ids && frame_ids.length > 0;
                        if (refraction_lines.some(line =>
                            !line.side || !line.erc || !line.ocular_dominance || (mustHaveFrame && !line.frame_id)
                        )) {
                            this.dialog.add(AlertDialog, {
                                title: _t("Data Tidak Lengkap"),
                                body: _t("Pastikan kolom *Side*, *ERC*, *Ocular Dominance*, dan *Frame* (jika membeli frame) terisi di setiap baris Refraction."),
                            });
                            return;
                        }
                        this.action.doAction({
                            type: "ir.actions.act_window_close",
                        });
                        resolve(true)
                    }
                },
                additionalContext: {
                    frame_ids: frame_ids,
                },
            });
        });

    },

    getLensProducts() {
        let orderlines = this.get_order().lines;

        let products = [];
        for (const key in orderlines) {
            var line = orderlines[key];
            if (line.product_id.is_lens) {
                for (var i=0; i<line.qty; i++) {
                    products.push({
                        line_index: parseInt(key) + i,
                        product_id: line.product_id.id
                    });
                }
            }
        }

        return products;
    },

    async cleanRefractionsData() {
        await this.data.call(
            'pos.order.refraction',
            "clean_refractions_data",
            [this.get_order().pos_reference]);
    },

});
