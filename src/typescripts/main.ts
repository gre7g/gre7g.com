import { $ } from "jquery";
import { Api } from "./api";
import { Navigator } from "./navigation";
import { Products } from "./products";
import { UI } from "./ui";

export let G_API: Api;
export let G_NAVIGATOR: Navigator;
export let G_PRODUCTS: Products;
export let G_UI: UI;

/**
 * Start-up code
 */
export class Main {
    async main(): Promise<void> {
        G_API = new Api();
        G_UI = new UI();
        G_NAVIGATOR = new Navigator();
        G_PRODUCTS = new Products();
        const response = await G_API.get("/api/v1/products");
        G_PRODUCTS.product_list = response.products;
        await G_NAVIGATOR.update(window.location.pathname);

        // TODO
        $("#test").on("click", async () => {
        });
    }
}
