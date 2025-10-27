/** @odoo-module */
import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class ProductPack extends Base {
    static pythonModel = "product.pack";
}
registry.category("pos_available_models").add(ProductPack.pythonModel, ProductPack);