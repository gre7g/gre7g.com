import { G_API, Main } from "./main";
import { $ } from "jquery";

export let G_MAIN = new Main();
G_MAIN.main();
$("#test").on("click", async () => {
    const x = await G_API.get("/api/v1/products");
    console.log(x);
});
