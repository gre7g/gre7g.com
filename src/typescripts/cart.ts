import { Product } from "./products";
import { G_API } from "./main";

export class Cart {
    contents: Product[] = [];

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
        if (
            !this.contents.some((item) => {
                if (item.product_id == product.product_id) {
                    // Found the item, so instead of adding a new entry, just increase how many are in the entry
                    item.quantity++;
                    return true;
                } else {
                    return false;
                }
            })
        ) {
            // Didn't find item, so add it
            const copy = {...product};
            copy.quantity = 1;
            this.contents.push(copy);
        }

        // Save the cart
        await G_API.put("/api/v1/cart", { products: this.contents });
    }
}
