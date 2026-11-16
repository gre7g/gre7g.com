import { G_API, G_CART, G_PRODUCTS, G_PUBSUB } from "./main";
import { Order, has_physical } from "./orders";
import { Product } from "./products";

class InertSection {
    section: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

    update() {}
}

class ListSection extends InertSection {
    unordered_list: JQuery<HTMLElement>;
    list_item: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        super(section);
        this.unordered_list = section.find("ul");
        this.list_item = section.find("li").detach();
    }
}

class ProductsUI extends ListSection {
    override async update() {
        this.unordered_list.empty();
        const populate_item = (product: Product) => {
            if (!product.parent_id) {
                const new_item = this.list_item.clone();
                new_item.find("a").attr("href", product.listing_path);
                new_item.find("img").attr("src", product.images[0]);
                new_item.find(".product-name").text(product.name);
                this.unordered_list.append(new_item);
            }
        };
        Object.values(G_PRODUCTS.product_list).forEach(populate_item);
    }
}

class ShopUI extends ProductsUI {}

class ProductUI {
    section: JQuery<HTMLElement>;
    product: Product | null = null;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

    private price(): string {
        if (this.product?.child_ids.length == 0) {
            return new Intl.NumberFormat("default", {
                style: "currency",
                currency: "USD",
            }).format(this.product.cost_per);
        } else {
            let min_cost = 9999.99;
            const check_min = (product: Product) => {
                if (this.product?.child_ids.includes(product.product_id) && product.cost_per < min_cost) {
                    min_cost = product.cost_per;
                }
            };
            Object.values(G_PRODUCTS.product_list).forEach(check_min);
            return `from ${min_cost}`;
        }
    }

    private media_links(): string {
        let links: string[] = [];
        const add_link = (product: Product) => {
            if (this.product?.child_ids.includes(product.product_id)) {
                links.push(`<a href="${product.listing_path}">${product.media}</a>`);
            }
        };
        Object.values(G_PRODUCTS.product_list).forEach(add_link);
        const formatter = new Intl.ListFormat("en", { style: "long", type: "conjunction" });
        return formatter.format(links);
    }

    async update() {
        $("#example").attr("href", this.product?.images[0]!);
        $("#price").text(this.price());
        const views = $("#views");
        const add_view = (path: string) => {
            const view = $(`<img src="${path}" />`);
            views.append(view);
        };
        this.product?.images?.forEach(add_view);
        this.section.find(".product-name").text(this.product?.name!);
        this.section.find(".description").html(this.product?.description!);
        const media = this.media_links();
        $("#add-to-cart").toggle(media == "");
        const media_element = this.section.find(".media");
        media_element.toggle(media != "");
        media_element.find("span").html(media);
    }
}

class CartUI extends ListSection {
    override async update() {
        this.unordered_list.empty();
        const add_item = (product: Product) => {
            const new_item = this.list_item.clone();
            new_item.find(".product-name").text(product.name);
            this.unordered_list.append(new_item);
        };
        Object.values(G_CART.contents).forEach(add_item);
    }
}

export class CheckoutUI extends CartUI {
    total = 0.0;

    override async update() {
        await super.update();
        $("#checkout-status").hide();

        // Calculate subtotal
        let subtotal = 0.0;
        const add_item = (product: Product) => {
            subtotal += product.quantity * product.cost_per;
        };
        G_CART.contents.forEach(add_item);
        let currency = new Intl.NumberFormat("default", {
            style: "currency",
            currency: "USD",
        }).format(subtotal);
        this.section.find("#subtotal span").text(currency);

        // Get shipping
        const response = await G_API.post("/api/v1/cart/shipping", {});
        currency = new Intl.NumberFormat("default", {
            style: "currency",
            currency: "USD",
        }).format(response?.shipping_cost);
        this.section.find("#shipping span").text(currency);

        // Calculate total
        this.total = subtotal + response?.shipping_cost;
        currency = new Intl.NumberFormat("default", {
            style: "currency",
            currency: "USD",
        }).format(this.total);
        this.section.find("#total span").text(currency);

        // Login status message
        const login_status = $("#login_status");
        const place_order = $("#place_order");
        switch (response.user_status) {
            case "logged_in":
                login_status.hide();
                place_order.show();
                break;
            case "may_log_in":
                login_status.show();
                login_status.find("span").html(`Please consider logging in or creating an
account. Yes, I know we all hate having to make an account on every freakin’ site we visit, but having an account makes 
things so much easier if you ever wish to access or contact me about an order. I promise not to share your address, and 
I won't spam you.`);
                place_order.show();
                break;
            case "must_log_in":
                login_status.show();
                login_status.find("span").html(`Digital downloads <em>must</em> be tied 
to an account. Yes, I know we all hate having to make an account on every freakin’ site we visit, but I promise not to 
share your address, and I won't spam you.`);
                place_order.hide();
                break;
        }
    }
}

class DownloadsUI extends ListSection {
    downloads: Record<string, string> = {};

    override async update() {
        this.unordered_list.empty();
        const populate_item = (value: [string, string]) => {
            let [filename, url] = value;
            const new_item = this.list_item.clone();
            const a = new_item.find("a");
            a.attr("href", url);
            a.text(filename);
            this.unordered_list.append(new_item);
        };
        Object.entries(this.downloads).forEach(populate_item);
    }
}

class OrderUI extends ListSection {
    order: Order | null = null;
    downloads: DownloadsUI;

    constructor(section: JQuery<HTMLElement>, downloads: JQuery<HTMLElement>) {
        const downloads_ui = new DownloadsUI(downloads);
        super(section);
        this.downloads = downloads_ui;
    }

    override async update() {
        if (this.order) {
            this.unordered_list.empty();
            const populate_item = async (product: Product) => {
                const new_item = this.list_item.clone();
                new_item.find("a").attr("href", product.listing_path);
                new_item.find(".product-name").text(product.name);
                const section = new_item.find(".downloads");
                if (Object.keys(product.downloads).length) {
                    this.downloads.unordered_list = section.find("ul");
                    this.downloads.downloads = product.downloads;
                    await this.downloads.update();
                } else {
                    section.hide();
                }
                this.unordered_list.append(new_item);
            };
            Object.values(this.order.products).forEach(populate_item);
        }
    }
}

class MinimalOrderUI extends ListSection {
    order: Order | null = null;

    override async update() {
        this.unordered_list.empty();
        if (this.order) {
            for (const product of this.order.products) {
                const new_item = this.list_item.clone();
                new_item.find(".product-name").text(product.name);
                this.unordered_list.append(new_item);
            }
        }
    }
}

class OrdersUI extends ListSection {
    orders: Order[] = [];
    order_ui: MinimalOrderUI;

    constructor(section: JQuery<HTMLElement>, order: JQuery<HTMLElement>) {
        const order_ui = new MinimalOrderUI(order);
        super(section);
        this.order_ui = order_ui;
    }

    override async update() {
        this.unordered_list.empty();
        for (const order of this.orders) {
            const new_item = this.list_item.clone();
            new_item.find("a").attr("href", `/order/${order.order_id}`);
            const section = new_item.find(".products");
            this.order_ui.unordered_list = section.find("ul");
            this.order_ui.order = order;
            await this.order_ui.update();
            this.unordered_list.append(new_item);
        }
    }
}

class ThankYou extends OrderUI {
    override async update() {
        super.update();

        if (this.order) {
            let message;
            if (has_physical(this.order)) {
                message = "We'll get those shipped right out to you!";
            } else {
                message = "You can download your purchases from the following links.";
            }
            this.section.find(".message").text(message);
        }
    }
}

export class UI {
    current_section = "products";
    sections = {
        about: new InertSection($("#about")),
        ai: new InertSection($("#ai")),
        appearances: new InertSection($("#appearances")),
        cart: new CartUI($("#cart")),
        checkout: new CheckoutUI($("#checkout")),
        contact: new InertSection($("#contact")),
        order: new OrderUI($("#order"), $("#order .downloads")),
        orders: new OrdersUI($("#orders"), $("#orders .products")),
        privacy: new InertSection($("#privacy")),
        product: new ProductUI($("#product-listing")),
        products: new ProductsUI($("#products")),
        shop: new ShopUI($("#shop")),
        sitemap: new InertSection($("#sitemap")),
        thank_you: new ThankYou($("#thank-you"), $("#thank-you .downloads")),
    };

    init() {
        G_PUBSUB.subscribe("navigate.bury_url", async (params) => {
            await this.bury_url(params.section, params.path);
        });
        G_PUBSUB.subscribe("ui.show_section", async (params) => {
            await this.show(params.section);
        });
        G_PUBSUB.subscribe("ui.update", async () => {
            await this.update_header();
        });
    }

    /**
     * Sets the URL bar to path and show the UI section but do not decode the URL.
     *
     * Call bury() without adding code to decode the path in Navigator. This allows the user to hit Back to the previous
     * page but not to bookmark the new page. Google searches haven't returned a standard name for this practice of
     * creating ephemeral routes, but I prefer "burying the URL".
     *
     * @param section   UI section to display
     * @param path      URL path to push
     */
    async bury_url(section: string, path: string) {
        history.pushState(null, "", path);
        G_PUBSUB.publish("ui.show_section", { section });
    }

    async show(section: string) {
        this.current_section = section;
        for (const [key, value] of Object.entries(this.sections)) {
            const show = key == section;
            value.section.toggle(show);
            if (show) {
                await value.update();
            }
        }
    }

    async update_header() {
        // Shopping cart contents
        $("#cart_button a").text(G_CART.contents.length == 0 ? "" : G_CART.contents.length);

        // Profile menu (if logged in) or login button (if not)
        const logged_in = await G_API.logged_in();
        $("#profile").toggle(logged_in);
        $("#nav-bar .login").toggle(!logged_in);
    }
}
