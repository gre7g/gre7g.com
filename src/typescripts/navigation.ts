import { G_PRODUCTS, G_UI } from "./main";

export class Navigator {
    async navigate(event: NavigateEvent) {
        const navigator = this;
        if (event.canIntercept && !event.downloadRequest && !event.formData && event.userInitiated) {
            const target_url = new URL(event.destination.url);
            event.intercept({
                async handler() {
                    event.preventDefault();
                    await navigator.go(target_url.pathname);
                },
            });
        }
    }

    async go(path: string): Promise<void> {
        if (path == "/shop") {
            console.log("Show shop"); // TODO
        } else if (path == "/login") {
            history.replaceState(null, "", "/login");
            await G_UI.show("products");
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
