import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    getPickedUpStatus(order) {
        const pickedUpState = order.picked_up_state
        if (pickedUpState === 'draft') {
            return 'Not Picked Up'
        } else if (pickedUpState === 'partially') {
            return 'Partially Picked Up'
        } else if (pickedUpState == 'done') {
            return 'Picked Up'
        }
        return ''
    }
})