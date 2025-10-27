/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

ProductCard.props = {
    ...ProductCard.props,
    availableQty: { type: true, optional: true}
};

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({
            availableQty: this.props.availableQty,
        });

        if (this.props?.onClick) {
            const originalClick = this.props.onClick;
            this.props.onClick = async (ev) => {
                const product = this.props.product;
                if (product.is_storable) {
                    const availableQty = this.props.availableQty
                    if (availableQty <= 0) {
                        this.dialog.add(
                            ConfirmationDialog,
                            {
                                title: _t("Out of Stock"),
                                body: _t("This product has no available quantity in stock. Contact your administrator for inventory updates."),
                            }
                        );
                        return;
                    }
                }
                originalClick(ev);
            };
        } else {
            console.warn('props.onClick tidak ada di', this.props.product?.display_name);
        };

        onMounted(async () => {
            await this._loadAvailableQty();
        })
    },

    async _loadAvailableQty() {
        const product = this.props.product;
        if (!product) return;

        let resp = await this.pos.data.read('product.product', [product.id], ['pack_ids', 'qty_available', 'is_storable', 'is_pack']);
        const prod = resp[0];

        if (prod.is_pack === true) {
            if (!prod.pack_ids || !prod.pack_ids.length) {
                this.state.availableQty = "";
                return;
            }

            const packIds = prod.pack_ids.map(p => p.id || p);
            const packProducts = await this.pos.data.read('product.pack', packIds, ['qty_available', 'is_storable']);
            const storableItems = packProducts.filter(p => p.is_storable);
            if (!storableItems.length) {
                this.state.availableQty = "";
                return;
            }

            const minQty = Math.min(...storableItems.map(item => item.qty_available || 0));
            this.state.availableQty = minQty;
            return;
        }

        if (!prod.is_storable) {
            this.state.availableQty = "";
            return;
        }

        this.state.availableQty = prod.qty_available ?? "";
    },

    get getAvailableQuantity() {
        return this.state.availableQty ?? "";
    },
});
