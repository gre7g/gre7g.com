import { $ } from "jquery";
import { Api } from "./api";
import { Cart } from "./cart";
import { Navigator } from "./navigation";
import { Products, Product } from "./products";
import { UI } from "./ui";

export let G_API: Api;
export let G_CART: Cart;
export let G_NAVIGATOR: Navigator;
export let G_PRODUCTS: Products;
export let G_UI: UI;

/**
 * Start-up code
 */
export class Main {
    async main(): Promise<void> {
        G_API = new Api();
        G_CART = new Cart();
        G_UI = new UI();
        G_NAVIGATOR = new Navigator();
        G_PRODUCTS = new Products();
        const response = await G_API.get("/api/v1/products");
        G_PRODUCTS.product_list = Object.fromEntries(
            response.products.map((product: Product) => [product.listing_path, product]),
        );
        await G_CART.load();
        await G_NAVIGATOR.go(window.location.pathname);

        const popstate = async () => {
            await G_NAVIGATOR.go(window.location.pathname);
        };
        $(window).on("popstate", popstate);
        const navigate_internal = async (event: MouseEvent) => {
            event.preventDefault();
            const href = $(event.currentTarget!).attr("href");
            history.pushState(null, "", href);
            await G_NAVIGATOR.go(href!);
        };
        $("a.internal").on("click", navigate_internal);
        const add_to_cart = async () => {
            if (G_UI.sections.product.product) {
                await G_CART.add(G_UI.sections.product.product);
                history.pushState(null, "", "/cart");
                await G_NAVIGATOR.go("/cart");
            }
        };
        $("#add-to-cart").on("click", add_to_cart);
        const checkout = async () => {
            // Note: We are setting the URL bar to /cart/checkout, but we're not decoding it. The Navigator class
            // doesn't decode that URL. Instead, we are manually advancing the view to the checkout page. Why? Because
            // having a name for this page will allow us to use the browser's back button, but bookmarking the checkout
            // page (or using the forward button from the cart) won't bring us back to it. This is a safety mechanism.
            // The user can bookmark the shopping cart page, but they will still need to click the Checkout button to
            // begin the checkout process. I call this "burying the URL".
            history.pushState(null, "", "/cart/checkout");
            await G_UI.show("checkout");
        };
        $("#checkout-button").on("click", checkout);
        const paypal_buttons = window.paypal.Buttons({
            style: { shape: "rect", layout: "vertical", color: "gold", label: "paypal" },
            message: { amount: 100 },
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
            async onApprove(data, actions) {
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
            },
        });
        paypal_buttons.render("#place_order");
    }
}
