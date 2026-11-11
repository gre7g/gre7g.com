import { loadScript, PayPalNamespace, OnApproveActions, OnApproveData } from "@paypal/paypal-js";

import { G_API, G_UI, G_SAM_OUTPUTS, G_NAVIGATOR } from "./main";
import {Order} from "./orders";

let G_SAVED_ERR_MSG = "";

export function load_paypal() {
    loadScript({
        clientId: G_SAM_OUTPUTS.paypal_client_id,
        buyerCountry: "US",
        currency: "USD",
        components: "buttons",
        enableFunding: "venmo,paylater,card",
    }).then((paypal: PayPalNamespace | null) => {
        if (paypal && paypal.Buttons) {
            const paypal_buttons = paypal.Buttons({
                style: { shape: "rect", layout: "vertical", color: "gold", label: "paypal" },
                message: { amount: G_UI.sections.checkout.total },

                async createOrder() {
                    try {
                        const order_data = await G_API.post("/api/v1/order", {});
                        return order_data.id;
                    } catch (error) {
                        G_SAVED_ERR_MSG = error instanceof Error ? error.message : JSON.stringify(error);
                        return null;
                    }
                },

                async onShippingAddressChange(data, actions) {
                    if (data.shippingAddress.countryCode !== "US") {
                        // TODO: make sure customers from other countries can by digital downloads
                        await actions.reject();
                    }
                },

                async onApprove(data: OnApproveData, actions: OnApproveActions) {
                    // Note: data.orderID is PayPal's order ID and order_id is ours. I suppose I could have used theirs
                    // as ours, but marries the code to theirs.
                    const order: Order = await G_API.put(`/api/v1/order/${data.orderID}`, {});
                    await G_NAVIGATOR.go(`/order/${order.order_id}`, true);
                },

                async onCancel(data) {
                    const status = $("#checkout-status");
                    status.text("Order cancelled");
                    status.show();
                },
                async onError(error) {
                    let message: string;
                    if (error instanceof Error) {
                        message =
                            error.message == "Expected an order id to be passed" ? G_SAVED_ERR_MSG : error.message;
                    } else {
                        message = JSON.stringify(error);
                    }
                    const status = $("#checkout-status");
                    status.text(message);
                    status.show();
                },
            });
            paypal_buttons.render("#place_order");
        }
    });
}
