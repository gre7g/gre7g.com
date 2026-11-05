import { $ } from "jquery";
import { signInWithRedirect } from "aws-amplify/auth";

import { Api } from "./api";
import { Cart } from "./cart";
import { Navigator } from "./navigation";
import { load_paypal } from "./paypal";
import { Products } from "./products";
import { UI } from "./ui";

interface SamOutputs {
    api_endpoint: string;
    audit_log: string;
    carts_table_name: string;
    cognito_host_name: string;
    cognito_login_url: string;
    orders_table_name: string;
    paypal_client_id: string;
    products_table_name: string;
    user_pool: string;
    user_pool_client: string;
    web_distribution: string;
    web_file_storage: string;
    website_url: string;
}

// Constants:
const CONFIG_URL = "/config.json";

// Globals:
export let G_API: Api;
export let G_CART: Cart;
export let G_NAVIGATOR: Navigator;
export let G_PRODUCTS: Products;
export let G_SAM_OUTPUTS: SamOutputs;
export let G_UI: UI;

/**
 * Start-up code
 */
export class Main {
    async add_to_cart() {
        if (G_UI.sections.product.product) {
            await G_CART.add(G_UI.sections.product.product);
            history.pushState(null, "", "/cart");
            await G_NAVIGATOR.go("/cart");
        }
    }

    async checkout() {
        // Note: We are setting the URL bar to /cart/checkout, but we're not decoding it. The Navigator class
        // doesn't decode that URL. Instead, we are manually advancing the view to the checkout page. Why? Because
        // having a name for this page will allow us to use the browser's back button, but bookmarking the checkout
        // page (or using the forward button from the cart) won't bring us back to it. This is a safety mechanism.
        // The user can bookmark the shopping cart page, but they will still need to click the Checkout button to
        // begin the checkout process. I call this "burying the URL".
        history.pushState(null, "", "/cart/checkout");
        await G_UI.show("checkout");
    }

    async main(): Promise<void> {
        G_API = new Api();
        G_CART = new Cart();
        G_NAVIGATOR = new Navigator();
        G_PRODUCTS = new Products();
        G_UI = new UI();

        const response: Response = await fetch(CONFIG_URL);
        G_SAM_OUTPUTS = await response.json();
        G_API.load();
        await G_PRODUCTS.load();
        await G_CART.load();
        await G_NAVIGATOR.go(window.location.pathname);

        $(window).on("popstate", async () => {
            await G_NAVIGATOR.go(window.location.pathname);
        });
        navigation.addEventListener("navigate", (event) => {
            G_NAVIGATOR.navigate(event);
        });
        $("#add-to-cart").on("click", async () => {
            await this.add_to_cart();
        });
        $("#checkout-button").on("click", async () => {
            await this.checkout();
        });
        $(".login").on("click", async () => {
            await signInWithRedirect();
        });
        load_paypal();
    }
}
