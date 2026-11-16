import { Product } from "./products";
import { G_API, G_PUBSUB } from "./main";

export class Cart {
    contents: Product[] = [];

    init(check_out:JQuery<HTMLElement>) {
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
            this.delete(params.product_index);
        });
        check_out.on("click", async () => {
            G_PUBSUB.publish("navigate.bury_url", { section: "checkout", path: "/cart/checkout" });
        });
    }

    async load() {
        const guest_id = localStorage.getItem("guest_id");
        if (guest_id) {
            G_API.guest_id = guest_id;
        } else {
            const response = await G_API.post("/api/v1/guest", {});
            G_API.guest_id = response.auth_token;
            localStorage.setItem("guest_id", response.auth_token);
        }

        const response = await G_API.get("/api/v1/cart");
        this.contents = response.products;
    }

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
            // Didn't find item, so add it
            const copy = { ...product };
            copy.quantity = 1;
            this.contents.push(copy);
        }
        G_PUBSUB.publish("navigate.go", { path: "/cart", save: true });

        // Save the cart
        await G_API.put("/api/v1/cart", { products: this.contents });
        G_PUBSUB.publish("ui.update", undefined);
    }

    async empty_cart() {
        this.contents = [];
        G_PUBSUB.publish("ui.update", undefined);
    }

    update_qty(product_index: number, quantity: number) {
        this.contents[product_index].quantity = quantity;
    }

    delete(product_index: number) {
        this.contents.splice(product_index, 1);
        G_PUBSUB.publish("cart.update", undefined);
    }
}
