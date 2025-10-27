/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.props.resModel === "wiz.stock.picking.scrap") {
            const observer = new MutationObserver(() => {
                const barcodeField = document.querySelector('div[name="barcode"] input.o_input');
                if (barcodeField) {
                    barcodeField.focus();
                    barcodeField.addEventListener("input", (ev) => {
                        clearTimeout(this.barcodeTimer);
                        this.barcodeTimer = setTimeout(() => {
                            const enterEvent = new KeyboardEvent("keydown", {
                                key: "Enter",
                                code: "Enter",
                                keyCode: 13,
                                which: 13,
                                bubbles: true,
                            });
                            ev.target.dispatchEvent(enterEvent);
                        }, 250);
                    });
                    observer.disconnect();
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true,
            });
        }
    },
});
