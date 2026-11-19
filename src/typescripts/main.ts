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

interface Events {
    "cart.empty": void;
    "cart.add": { product: Product };
    "cart.delete": { product_index: number };
    "cart.update": void;
    "cart.update_qty": { product_index: number; quantity: number };
    "navigate.bury_url": { section: string; path: string };
    "navigate.go": { path: string; save?: boolean };
    "ui.show_error": { message: string };
    "ui.show_info": { message: string };
    "ui.show_section": { section: string };
    "ui.update": void;
    "user.login": void;
    "user.logout": void;
}

// Constants:
const CONFIG_URL = "/config.json";

// Globals:
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

    async main(): Promise<void> {
        G_API = new Api();
        G_CART = new Cart($("#empty-cart"), $("#checkout-button"));
        G_PRODUCTS = new Products();
        G_PUBSUB = new PubSub<Events>();
        G_UI = new UI();

        const response: Response = await fetch(CONFIG_URL);
        G_SAM_OUTPUTS = await response.json();
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

        $(window).on("popstate", () => {
            G_PUBSUB.publish("navigate.go", { path: window.location.pathname });
        });
        load_paypal();
    }
}
