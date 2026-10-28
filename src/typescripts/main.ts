import { $ } from "jquery";
import { Api } from "./api";
import { Navigator } from "./navigation";
import { Products, Product } from "./products";
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
        console.log(response.products);
        G_PRODUCTS.product_list = Object.fromEntries(
            response.products.map((product: Product) => [product.listing_path, product]),
        );
        console.log(G_PRODUCTS);
        await G_NAVIGATOR.go(window.location.pathname);

        $(window).on("popstate", async () => {
            await G_NAVIGATOR.go(window.location.pathname);
        });
        $("a.internal").on("click", async (event) => {
            event.preventDefault();
            const href = $(event.currentTarget).attr("href");
            history.pushState(null, "", href);
            await G_NAVIGATOR.go(href!);
        });
        $("#add-to-cart").on("click", async (event) => {
            // await TODO
        });

        // TODO
        $("#test").on("click", async () => {});
    }
}
