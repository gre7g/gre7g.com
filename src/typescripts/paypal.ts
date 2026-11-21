import { $ } from "jquery";
import { loadScript, PayPalNamespace, OnApproveActions, OnApproveData } from "@paypal/paypal-js";

import { G_API, G_UI, G_SAM_OUTPUTS, G_CART, G_PUBSUB } from "./main";

// createOrder() can't return an error through PayPal, so it saves the message here for onError() to show instead of
// PayPal's generic one
let G_SAVED_ERR_MSG = "";

/**
 * Load the PayPal SDK and render its payment buttons into #place_order in the checkout section.
 *
 * The buttons drive the order flow: createOrder() creates the order through our API, onApprove() confirms it and
 * shows the thank-you page, and onCancel()/onError() show a message in #checkout-status.
 */
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

                /**
                 * Create an order through our API when the user clicks a PayPal button.
                 *
                 * @returns    PayPal's order ID, or null if the API call failed
                 */
                async createOrder() {
                    try {
                        const order_data = await G_API.post("/api/v1/order", {});
                        return order_data.id;
                    } catch (error) {
                        G_SAVED_ERR_MSG = error instanceof Error ? error.message : JSON.stringify(error);
                        return null;
                    }
                },

                /**
                 * Only US shipping addresses are accepted.
                 */
                async onShippingAddressChange(data, actions) {
                    if (data.shippingAddress.countryCode !== "US") {
                        // TODO: make sure customers from other countries can by digital downloads
                        await actions.reject();
                    }
                },

                /**
                 * The user approved the payment, so confirm the order, show the thank-you page, and empty the cart.
                 */
                async onApprove(data: OnApproveData, actions: OnApproveActions) {
                    // Note: data.orderID is PayPal's order ID and order_id is ours. I suppose I could have used theirs
                    // as ours, but marries the code to theirs.
                    G_UI.sections.thank_you.order = await G_API.put(`/api/v1/order/${data.orderID}`, {});
                    G_PUBSUB.publish("navigate.bury_url", { section: "thank_you", path: "/thank-you" });
                    await G_CART.empty_cart();
                },

                /**
                 * The user closed the PayPal window without paying.
                 */
                async onCancel(data) {
                    const status = $("#checkout-status");
                    status.text("Order cancelled");
                    status.show();
                },
                /**
                 * PayPal reported an error.
                 */
                async onError(error) {
                    let message: string;
                    if (error instanceof Error) {
                        // PayPal reports this when createOrder() returned null, so show the reason we saved
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
