import { G_PRODUCTS } from "./main";

export class Navigator {
    async update(path: string): Promise<void> {
        if (path == "/shop") {
            console.log("Show shop"); // TODO
        } else if (path == "/appearances") {
            console.log("Show appearances"); // TODO
        } else if (path == "/contact") {
            console.log("Show contact form"); // TODO
        } else if (path == "/about") {
            console.log("Show about the author"); // TODO
        } else if (path == "/user/profile") {
            console.log("Show user profile"); // TODO
        } else if (path == "/user/logout") {
            console.log("Log the user out"); // TODO
        } else if (path == "/cart") {
            console.log("Show the shopping cart"); // TODO
        } else if (path == "/privacy") {
            console.log("Show privacy policy"); // TODO
        } else if (path == "/sitemap") {
            console.log("Show the sitemap"); // TODO
        } else if (G_PRODUCTS.has_path(path)) {
            await G_PRODUCTS.show_path(path);
        } else {
            G_PRODUCTS.show_products();
            console.log("Show the default view"); // TODO
        }
    }
}
