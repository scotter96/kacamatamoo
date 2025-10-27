import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ReturnButton } from "./return_button";
import { RefractionButton } from "./refraction_button";
import { patch } from "@web/core/utils/patch";


patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        RefractionButton,
        ReturnButton,
    }
});
