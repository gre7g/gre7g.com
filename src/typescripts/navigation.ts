import { G_API, G_PRODUCTS, G_PUBSUB, G_UI } from "./main";

/**
 * Client-side router: turns a URL path into the UI section to show.
 *
 * Subscribes to "navigate.go" and intercepts user-initiated browser navigations (via the Navigation API) so
 * that links within the site don't reload the page.
 */
export class Navigator {
    /**
     * Subscribe to "navigate.go" and start intercepting browser navigations.
     */
    init() {
        G_PUBSUB.subscribe("navigate.go", async (params) => {
            await this.go(params.path, params.save);
        });
        navigation.addEventListener("navigate", async (event) => {
            await this.navigate(event);
        });
    }

    /**
     * Handle a browser navigation by routing it in-page instead of loading a new page.
     *
     * Downloads, form submissions, and navigations the page didn't start from a user action are left alone.
     *
     * @param event   Navigation API event
     */
    async navigate(event: NavigateEvent) {
        // `this` isn't the Navigator inside handler(), so keep a reference
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

    /**
     * Show the section for a URL path.
     *
     * Fixed paths are matched first, then product listing paths, then /user/order/{order_id}. Anything else shows
     * the shop page.
     *
     * @param path    URL path to route
     * @param save    If true, push the path onto the browser history
     */
    async go(path: string, save?: boolean): Promise<void> {
        if (save) {
            history.pushState(null, "", path);
        }
        switch (path) {
            case "/articles/ai":
                G_PUBSUB.publish("ui.show_section", { section: "ai" });
                break;
            case "/articles/privacy":
                G_PUBSUB.publish("ui.show_section", { section: "privacy" });
                break;
            case "/articles/sitemap":
                G_PUBSUB.publish("ui.show_section", { section: "sitemap" });
                break;
            case "/gre7g/about":
                G_PUBSUB.publish("ui.show_section", { section: "about" });
                break;
            case "/gre7g/appearances":
                G_PUBSUB.publish("ui.show_section", { section: "appearances" });
                break;
            case "/gre7g/contact":
                G_PUBSUB.publish("ui.show_section", { section: "contact" });
                break;
            case "/login": // Bounce from Cognito
                history.replaceState(null, "", "/login");
                G_PUBSUB.publish("ui.show_section", { section: "products" });
                break;
            case "/shop/products":
                G_PUBSUB.publish("ui.show_section", { section: "products" });
                break;
            case "/user/cart":
                G_PUBSUB.publish("ui.show_section", { section: "cart" });
                break;
            case "/user/orders":
                await G_PUBSUB.publish_async("orders.fetch", undefined);
                G_PUBSUB.publish("ui.show_section", { section: "orders" });
                break;
            case "/user/password":
                G_PUBSUB.publish("ui.show_section", { section: "password" });
                break;
            default:
                if (G_PRODUCTS.has_path(path)) {
                    await G_PRODUCTS.show_path(path);
                } else {
                    const parts = path.split("/");
                    if (parts.length == 4 && parts[1] == "user" && parts[2] == "order") {
                        // URL: /user/order/{order_id}
                        try {
                            const order = await G_API.get(`/api/v1/order/${parts[3]}`);
                            G_UI.sections.order.order = order.order;
                        } catch {
                            G_UI.sections.order.order = null;
                        }
                        // The order page has handling logic if the user isn't logged in
                        G_PUBSUB.publish("ui.show_section", { section: "order" });
                    } else {
                        G_PUBSUB.publish("ui.show_section", { section: "shop" });
                    }
                }
        }
    }
}
