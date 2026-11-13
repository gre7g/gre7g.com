import { G_API, G_PRODUCTS, G_UI } from "./main";

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

    async go(path: string, save?: boolean): Promise<void> {
        if (save) {
            history.pushState(null, "", path);
        }
        switch (path) {
            case "/ai":
                await G_UI.show("ai");
                break;
            case "/appearances":
                await G_UI.show("appearances");
                break;
            case "/cart":
                await G_UI.show("cart");
                break;
            case "/gre7g/about":
                await G_UI.show("about");
                break;
            case "/gre7g/contact":
                await G_UI.show("contact");
                break;
            case "/login":
                history.replaceState(null, "", "/login");
                await G_UI.show("products");
                break;
            case "/logout":
                console.log("Log the user out"); // TODO
                break;
            case "/privacy":
                await G_UI.show("privacy");
                break;
            case "/sitemap":
                await G_UI.show("sitemap");
                break;
            case "/products":
                await G_UI.show("products");
                break;
            case "/user/logout":
                await G_API.logout();
                await G_UI.show("shop");
                break;
            case "/user/orders":
                await G_UI.show("orders");
                break;
            case "/user/profile":
                console.log("Show user profile"); // TODO
                break;
            default:
                if (G_PRODUCTS.has_path(path)) {
                    await G_PRODUCTS.show_path(path);
                } else {
                    const parts = path.split("/");
                    if (parts.length == 3 && parts[1] == "order") {
                        // URL: /order/{order_id}
                        const order = await G_API.get(`/api/v1/order/${parts[2]}`);
                        G_UI.sections.order.order = order.order;
                        await G_UI.show("order");
                    } else {
                        await G_UI.show("shop");
                    }
                }
        }
    }
}
