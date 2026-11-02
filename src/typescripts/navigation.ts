import { G_PRODUCTS, G_UI } from "./main";
import { $ } from "jquery";
import ClickEvent = JQuery.ClickEvent;

export class Navigator {
    async navigate_internal(event: ClickEvent) {
        event.preventDefault();
        const href = $(event.currentTarget!).attr("href");
        history.pushState(null, "", href);
        await this.go(href!);
    }

    async go(path: string): Promise<void> {
        if (path == "/shop") {
            console.log("Show shop"); // TODO
        } else if (path == "/gre7g/appearances") {
            console.log("Show appearances"); // TODO
        } else if (path == "/gre7g/contact") {
            console.log("Show contact form"); // TODO
        } else if (path == "/gre7g/about") {
            console.log("Show about the author"); // TODO
        } else if (path == "/user/profile") {
            console.log("Show user profile"); // TODO
        } else if (path == "/user/logout") {
            console.log("Log the user out"); // TODO
        } else if (path == "/cart") {
            await G_UI.show("cart");
        } else if (path == "/privacy") {
            console.log("Show privacy policy"); // TODO
        } else if (path == "/sitemap") {
            console.log("Show the sitemap"); // TODO
        } else if (G_PRODUCTS.has_path(path)) {
            await G_PRODUCTS.show_path(path);
        } else {
            await G_UI.show("products");
        }
    }
}
