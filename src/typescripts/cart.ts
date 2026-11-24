import { Product } from "./products";
import { G_API, G_CART, G_PUBSUB } from "./main";

/**
 * The shopping cart contents and the parts of the cart page that depend on whether it's empty.
 *
 * The cart is saved through the API, which identifies it by the guest ID. Subscribes to "cart.empty",
 * "cart.add", "cart.update_qty", "cart.delete", "cart.update", and "ui.update".
 */
export class Cart {
    contents: Product[] = [];
    // "Your cart is empty" message
    empty: JQuery<HTMLElement>;
    // Checkout button
    button: JQuery<HTMLElement>;

    constructor(empty: JQuery<HTMLElement>, button: JQuery<HTMLElement>) {
        this.empty = empty;
        this.button = button;
    }

    /**
     * Subscribe to the cart events and hook up the checkout button.
     */
    init() {
        G_PUBSUB.subscribe("cart.empty", async () => {
            await this.empty_cart();
        });
        G_PUBSUB.subscribe("cart.add", async (params) => {
            await this.add(params.product);
        });
        G_PUBSUB.subscribe("cart.update_qty", async (params) => {
            this.update_qty(params.product_index, params.quantity);
        });
        G_PUBSUB.subscribe("cart.delete", async (params) => {
            await this.delete(params.product_index);
        });
        G_PUBSUB.subscribe("ui.update", async (params) => {
            this.update();
        });
        G_PUBSUB.subscribe("cart.update", async (params) => {
            this.update();
        });
        // Checkout gets a buried URL so it can't be bookmarked (see UI.bury_url())
        this.button.on("click", async () => {
            G_PUBSUB.publish("navigate.bury_url", { section: "checkout", path: "/user/cart/checkout" });
        });
    }

    /**
     * Get or create a guest ID, then fetch the cart from the API.
     *
     * The guest ID is kept in localStorage so the cart survives page reloads.
     */
    async load() {
        const guest_id = localStorage.getItem("guest_id");
        if (guest_id) {
            G_API.guest_id = guest_id;
        } else {
            const response = await G_API.post("/api/v1/guest", {}, true);
            G_API.guest_id = response.auth_token;
            localStorage.setItem("guest_id", response.auth_token);
        }

        const response = await G_API.get("/api/v1/cart", true);
        this.contents = response.products;
        G_PUBSUB.publish("ui.update", undefined);
    }

    /**
     * Add one of a product to the cart, show the cart, and save it.
     *
     * @param product     Product to add
     */
    async add(product: Product) {
        // Search through the cart contents to see if we already have one
        const item_is_product = (item: Product) => {
            if (item.product_id == product.product_id) {
                // Found the item, so instead of adding a new entry, just increase how many are in the entry
                item.quantity++;
                return true;
            } else {
                return false;
            }
        };
        if (!this.contents.some(item_is_product)) {
            // Didn't find item. Add a copy so the catalog entry isn't changed.
            const copy = { ...product };
            copy.quantity = 1;
            this.contents.push(copy);
        }
        G_PUBSUB.publish("navigate.go", { path: "/user/cart", save: true });

        // Save the cart
        await G_API.put("/api/v1/cart", { products: this.contents }, true);
        G_PUBSUB.publish("ui.update", undefined);
    }

    /**
     * Empty the cart.
     */
    async empty_cart() {
        this.contents = [];
        await G_API.put("/api/v1/cart", { products: this.contents }, true);
        G_PUBSUB.publish("ui.update", undefined);
    }

    /**
     * Change the quantity of a cart entry.
     *
     * @param product_index   Index into contents
     * @param quantity        New quantity
     */
    async update_qty(product_index: number, quantity: number) {
        this.contents[product_index].quantity = quantity;
        await G_API.put("/api/v1/cart", { products: this.contents }, true);
    }

    /**
     * Remove an entry from the cart.
     *
     * @param product_index   Index into contents
     */
    async delete(product_index: number) {
        this.contents.splice(product_index, 1);

        // Save the cart
        await G_API.put("/api/v1/cart", { products: this.contents }, true);
        G_PUBSUB.publish("cart.update", undefined);
    }

    /**
     * Show the "empty" message and disable checkout when there's nothing in the cart.
     */
    update() {
        const empty = this.contents.length == 0;
        this.empty.toggle(empty);
        this.button.prop("disabled", empty);
    }

    /**
     * Mark cart items as out of stock.
     *
     * @param product_ids   List of product IDs that are out of stock.
     */
    out_of_stock(product_ids: string[]) {
        for (const product_id of product_ids) {
            this.contents.some((item) => {
                if (item.product_id == product_id) {
                    item.quantity = 0;
                    return true;
                }
                return false;
            });
        }

        // Return to the cart page, show an error, update the cart, and reload the inventory
        G_PUBSUB.publish("navigate.go", { path: "/user/cart", save: true });
        G_PUBSUB.publish("ui.show_error", {
            message: "Sadly, your order had to be aborted. One or more items in your cart are no longer available.",
        });
        void G_API.put("/api/v1/cart", { products: this.contents });
        void G_CART.load();
    }
}
