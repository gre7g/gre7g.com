import { $ } from "jquery";
import { Api } from "./api";
import { Navigator } from "./navigation";
import { Products } from "./products";

export let G_API: Api;
export let G_NAVIGATOR: Navigator;
export let G_PRODUCTS: Products;

/**
 * Start-up code
 */
export class Main {
    async main(): Promise<void> {
        G_API = new Api();
        G_NAVIGATOR = new Navigator();
        G_PRODUCTS = new Products();
        G_PRODUCTS.product_list = await G_API.get("/api/v1/products");
        await G_NAVIGATOR.update(window.location.pathname);

        // TODO
        $("#test").on("click", async () => {
        });
    }
}
