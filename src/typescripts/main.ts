import { $ } from "jquery";

import { Api } from "./api";
import { Cart } from "./cart";
import { Contact } from "./contact";
import { Navigator } from "./navigation";
import { load_paypal } from "./paypal";
import { Product, Products } from "./products";
import { PubSub } from "./pubsub";
import { Status } from "./status";
import { UI } from "./ui";

/**
 * Deployment outputs from the SAM stack, served to the browser as /config.json.
 *
 * Only a few of these are used by the front end (Cognito, PayPal, website URL, and the vacation message); the rest
 * come along for the ride because the same file is generated for the back end.
 */
interface SamOutputs {
    api_endpoint: string;
    audit_log: string;
    carts_table_name: string;
    cognito_host_name: string;
    orders_table_name: string;
    paypal_client_id: string;
    products_table_name: string;
    user_pool: string;
    user_pool_client: string;
    web_distribution: string;
    web_file_storage: string;
    website_url: string;
    // Non-empty when the shop is closed; shown to the user as a warning banner
    vacation: string;
}

/**
 * Map of every PubSub event name to the type of its payload.
 *
 * PubSub<Events> uses this to type-check both publishers and subscribers. Events with a `void` payload are
 * published with `undefined`.
 */
interface Events {
    // Clear the cart (e.g. after an order is placed)
    "cart.empty": void;
    // Add one of a product to the cart
    "cart.add": { product: Product };
    // Remove the cart entry at the given index
    "cart.delete": { product_index: number };
    // Cart contents changed, so re-render anything that shows them
    "cart.update": void;
    // Quantity input for a cart entry changed
    "cart.update_qty": { product_index: number; quantity: number };
    // Fetch orders from the database
    "orders.fetch": void;
    // Show a section at an ephemeral URL (see UI.bury_url())
    "navigate.bury_url": { section: string; path: string };
    // Route to a path; save pushes it onto the browser history
    "navigate.go": { path: string; save?: boolean };
    // Close every drop-down menu
    "ui.close_dropdowns": void;
    // Show an error in the status bar
    "ui.show_error": { message: string };
    // Show an info message in the status bar
    "ui.show_info": { message: string };
    // Show the named section of UI.sections and hide the rest
    "ui.show_section": { section: string };
    // Show a warning in the status bar
    "ui.show_warning": { message: string };
    // Something global changed (login state, cart load, etc.), so refresh whatever depends on it
    "ui.update": void;
    // Start/finish a Cognito login or logout
    "user.login": void;
    "user.logout": void;
}

// Constants:
const CONFIG_URL = "/config.json";

// Globals:
// These are assigned in Main.main() rather than at import time so that module load order doesn't matter and so
// tests can mock the ./main module and supply their own.
export let G_API: Api;
export let G_CART: Cart;
export let G_PRODUCTS: Products;
export let G_PUBSUB: PubSub<Events>;
export let G_SAM_OUTPUTS: SamOutputs;
export let G_UI: UI;

/**
 * Start-up code
 */
export class Main {
    contact = new Contact($("#contact"));
    navigator = new Navigator();
    status = new Status($("#status"));

    /**
     * Create the global singletons, load configuration and data, wire up event handlers, and route to the URL.
     *
     * Order matters here: the config must be loaded before the API is configured, the API must be configured before
     * products and cart are fetched, and subscribers must be registered before the initial "navigate.go" is published.
     */
    async main(): Promise<void> {
        G_API = new Api();
        G_CART = new Cart($("#empty-cart"), $("#checkout-button"));
        G_PRODUCTS = new Products();
        G_PUBSUB = new PubSub<Events>();
        G_UI = new UI();

        const response: Response = await fetch(CONFIG_URL);
        G_SAM_OUTPUTS = await response.json();
        // ?auth=<id> lets local testing impersonate a user when dummy authentication is enabled
        G_API.dummy_auth = new URLSearchParams(window.location.search).get("auth") ?? "";
        G_API.load();
        G_CART.init();
        this.contact.init();
        await G_PRODUCTS.load();
        await G_CART.load();
        this.navigator.init();
        this.status.init();
        G_API.init();
        G_UI.init();
        G_PUBSUB.publish("navigate.go", { path: window.location.pathname });
        G_PUBSUB.publish("ui.update", undefined);

        // Browser Back/Forward: re-route to whatever URL the browser is now showing
        $(window).on("popstate", () => {
            G_PUBSUB.publish("navigate.go", { path: window.location.pathname });
        });
        // Links marked .internal are handled in-page rather than reloading the site
        $(".internal").on("click", (event) => {
            event.preventDefault();
            const href = $(event.target).closest("a").attr("href");
            if (href) {
                G_PUBSUB.publish("navigate.go", { path: href, save: true });
            }
        });
        $("a.login").on("click", () => {
            G_PUBSUB.publish("user.login", undefined);
        });
        $(".logout").on("click", () => {
            G_PUBSUB.publish("user.logout", undefined);
        });
        // Loaded asynchronously; the buttons render into the checkout section when ready
        load_paypal();
        if (G_SAM_OUTPUTS.vacation) {
            G_PUBSUB.publish("ui.show_warning", { message: G_SAM_OUTPUTS.vacation });
        }
    }
}
