import { loadScript, PayPalNamespace, OnApproveActions, OnApproveData } from "@paypal/paypal-js";

import { G_API, G_UI, G_SAM_OUTPUTS } from "./main";

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
                    } catch (response) {
                        G_SAVED_ERR_MSG = response.statusText ?? JSON.stringify(response);
                        return null;
                    }
                },

                async onShippingAddressChange(data, actions) {
                    if (data.shippingAddress.countryCode !== "US") {
                        await actions.reject();
                    }
                },

                async onApprove(data: OnApproveData, actions: OnApproveActions) {
                    await G_API.put(`/api/v1/order/${data.orderID}`, {});
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
