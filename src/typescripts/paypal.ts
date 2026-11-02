import { loadScript, PayPalNamespace, OnApproveActions, OnApproveData } from "@paypal/paypal-js";

import { G_API, G_UI, G_SAM_OUTPUTS } from "./main";

export function load_paypal() {
    loadScript({
        clientId: G_SAM_OUTPUTS.paypal_client_id,
        buyerCountry: "US",
        currency: "USD",
        components: "buttons",
        enableFunding: "venmo,paylater,card"
    }).then((paypal: PayPalNamespace | null) => {
        if (paypal && paypal.Buttons) {
            const paypal_buttons = paypal.Buttons({
                style: { shape: "rect", layout: "vertical", color: "gold", label: "paypal" },
                message: { amount: G_UI.sections.checkout.total },

                async createOrder() {
                    try {
                        const order_data = await G_API.post("/api/v1/order", {});
                        if (order_data.id) {
                            return order_data.id;
                        }

                        const error_detail = order_data?.details?.[0];
                        const error_message = error_detail
                            ? `${error_detail.issue} ${error_detail.description} (${order_data.debug_id})`
                            : JSON.stringify(order_data);
                        throw new Error(error_message);
                    } catch (error) {
                        console.error(error);
                    }
                },

                async onApprove(data: OnApproveData, actions: OnApproveActions) {
                    try {
                        const order_data = await G_API.put(`/api/v1/order/${data.orderID}`, {});
                        const error_detail = order_data?.details?.[0];

                        if (error_detail?.issue === "INSTRUMENT_DECLINED") {
                            return actions.restart();
                        } else if (error_detail) {
                            throw new Error(`${error_detail.description} (${order_data.debug_id})`);
                        } else if (!order_data.purchase_units) {
                            throw new Error(JSON.stringify(order_data));
                        } else {
                            console.log("success", order_data);
                            //                   const transaction =
                            //                       order_data?.purchase_units?.[0]?.payments?.captures?.[0] ||
                            //                       order_data?.purchase_units?.[0]?.payments?.authorizations?.[0];
                            //                   resultMessage(
                            //                       `Transaction ${transaction.status}: ${transaction.id}<br>
                            // <br>See console for all available details`,
                            //                   );
                            //                   console.log("Capture result", order_data, JSON.stringify(order_data, null, 2));
                        }
                    } catch (error) {
                        console.error(error);
                        // resultMessage(`Sorry, your transaction could not be processed...<br><br>${error}`);
                    }
                }
            });
            paypal_buttons.render("#place_order");
        }
    });
}
