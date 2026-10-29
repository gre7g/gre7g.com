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

        $(window).on("popstate", async () => {
            await G_NAVIGATOR.go(window.location.pathname);
        });
        $("a.internal").on("click", async (event) => {
            event.preventDefault();
            const href = $(event.currentTarget).attr("href");
            history.pushState(null, "", href);
            await G_NAVIGATOR.go(href!);
        });
        $("#add-to-cart").on("click", async () => {
            if (G_UI.sections.product.product) {
                await G_CART.add(G_UI.sections.product.product);
                history.pushState(null, "", "/cart");
                await G_NAVIGATOR.go("/cart");
            }
        });
        $("#checkout-button").on("click", async () => {
            // Note: We are setting the URL bar to /cart/checkout, but we're not decoding it. The Navigator class
            // doesn't decode that URL. Instead, we are manually advancing the view to the checkout page. Why? Because
            // having a name for this page will allow us to use the browser's back button, but bookmarking the checkout
            // page (or using the forward button from the cart) won't bring us back to it. This is a safety mechanism.
            // The user can bookmark the shopping cart page, but they will still need to click the Checkout button to
            // begin the checkout process. I call this "burying the URL".
            history.pushState(null, "", "/cart/checkout");
            await G_UI.show("checkout");
        });
    }
}
