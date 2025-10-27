import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";
import { patch } from "@web/core/utils/patch";

patch(LoginScreen.prototype, {
    clickBack() {
        this.pos.closePos();
    }
});