import { $ } from "jquery";
import { Api } from "./api";
import { Navigator } from "./navigation";
import { Products } from "./products";

export let G_MAIN: Main;
export let G_API: Api;
export let G_NAVIGATOR: Navigator;
export let G_PRODUCTS: Products;

/**
 * Start-up code
 */
class Main {}

async function main(): Promise<void> {
    G_MAIN = new Main();
    G_API = new Api();
    G_NAVIGATOR = new Navigator();
    G_PRODUCTS = new Products();
    await G_NAVIGATOR.update(window.location.pathname);
}

console.log("setting main");
(window as any).main = main;
$("#test").on("click", async () => {
    const x = await G_API.get("/api/v1/products");
    console.log(x);
});
