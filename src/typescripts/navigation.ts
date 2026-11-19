import { G_API, G_PRODUCTS, G_PUBSUB, G_UI } from "./main";
import { Order } from "./orders";

export class Navigator {
    init() {
        G_PUBSUB.subscribe("navigate.go", async (params) => {
            await this.go(params.path, params.save);
        });
        navigation.addEventListener("navigate", async (event) => {
            await this.navigate(event);
        });
    }

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
                await G_UI.sections.orders.fetch();
                break;
            case "/user/profile":
                G_PUBSUB.publish("ui.show_section", { section: "password" });
                break;
            default:
                if (G_PRODUCTS.has_path(path)) {
                    await G_PRODUCTS.show_path(path);
                } else {
                    const parts = path.split("/");
                    if (parts.length == 4 && parts[1] == "user" && parts[2] == "order") {
                        // URL: /user/order/{order_id}
                        const order = await G_API.get(`/api/v1/order/${parts[3]}`);
                        G_UI.sections.order.order = order.order;
                        G_PUBSUB.publish("ui.show_section", { section: "order" });
                    } else {
                        G_PUBSUB.publish("ui.show_section", { section: "shop" });
                    }
                }
        }
    }
}
