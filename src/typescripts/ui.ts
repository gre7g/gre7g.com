import { G_API, G_CART, G_PRODUCTS, G_PUBSUB, G_UI } from "./main";
import { Order, has_physical } from "./orders";
import { Product } from "./products";
import { $ } from "jquery";
import { DropDown } from "./drop_down";

function update_cost(select: JQuery<HTMLElement>, cost: number) {
    const currency = new Intl.NumberFormat("default", {
        style: "currency",
        currency: "USD",
    }).format(cost);
    select.text(currency);
}

class InertSection {
    section: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

    init() {}
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

class ProductUI extends InertSection {
    product: Product | null = null;

    override init() {
        this.section.find("button").on("click", () => {
            this.add_to_cart();
        });
    }

    add_to_cart() {
        if (G_UI.sections.product.product) {
            G_PUBSUB.publish("cart.add", { product: G_UI.sections.product.product });
        }
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

    override async update() {
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
    override init() {
        G_PUBSUB.subscribe("cart.update_qty", async (params) => {
            this.update_qty(params.product_index, params.quantity);
        });
        G_PUBSUB.subscribe("cart.update", async () => {
            await this.update();
        });
    }

    update_qty(product_index: number, quantity: number) {
        const select = this.section.find(`li:nth-child(${product_index + 1}) .ext-cost`);
        update_cost(select, G_CART.contents[product_index].cost_per * quantity);
    }

    override async update() {
        this.unordered_list.empty();
        for (const [index, product] of G_CART.contents.entries()) {
            const new_item = this.list_item.clone();
            new_item.data("product_index", index);
            new_item.find(".product-name").text(product.name);
            const quantity = new_item.find("input");
            quantity.val(product.quantity);
            quantity.on("input", function () {
                const input = $(this);
                const product_index = input.closest("li").data("product_index");
                G_PUBSUB.publish("cart.update_qty", { product_index, quantity: parseInt(input.val() ?? "0", 10) });
            });
            update_cost(new_item.find(".ext-cost"), product.cost_per * product.quantity);
            new_item.find("button").on("click", function () {
                const product_index = $(this).closest("li").data("product_index");
                G_PUBSUB.publish("cart.delete", { product_index });
            });
            this.unordered_list.append(new_item);
        }
    }
}

export class CheckoutUI extends CartUI {
    total = 0.0;

    override init() {
        this.section.find("button.login").on("click", async () => {
            G_PUBSUB.publish("user.login", undefined);
        });
    }

    override async update() {
        await super.update();
        $("#checkout-status").hide();

        // Calculate subtotal
        let subtotal = 0.0;
        const add_item = (product: Product) => {
            subtotal += product.quantity * product.cost_per;
        };
        G_CART.contents.forEach(add_item);
        update_cost(this.section.find("#subtotal span"), subtotal);

        // Get shipping
        const response = await G_API.post("/api/v1/cart/shipping", {});
        update_cost(this.section.find("#shipping span"), response?.shipping_cost);

        // Calculate total
        this.total = subtotal + response?.shipping_cost;
        update_cost(this.section.find("#total span"), this.total);

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
            const date: Date = new Date(this.order.timestamp);
            this.section.find(".timestamp").text(date.toLocaleDateString() + ":");
            for (const product of this.order.products) {
                const new_item = this.list_item.clone();
                const item_link = new_item.find("a");
                item_link.attr("href", product.listing_path);
                item_link.text(product.name);
                const quantity = new_item.find(".quantity");
                if (product.quantity > 1) {
                    quantity.text(`Qty: ${product.quantity}`);
                } else {
                    quantity.hide();
                }
                update_cost(new_item.find(".amount"), product.cost_per * product.quantity);
                const section = new_item.find(".downloads");
                if (Object.keys(product.downloads).length) {
                    this.downloads.unordered_list = section.find("ul");
                    this.downloads.downloads = product.downloads;
                    await this.downloads.update();
                } else {
                    section.hide();
                }
                this.unordered_list.append(new_item);
            }
            update_cost(this.section.find(".subtotal .amount"), this.order.subtotal_cost);
            update_cost(this.section.find(".shipping .amount"), this.order.shipping_cost);
            const discount = this.section.find(".discount");
            if (this.order.discount) {
                update_cost(discount.find(".amount"), this.order.discount);
                discount.show();
            } else {
                discount.hide();
            }
            update_cost(this.section.find(".total .amount"), this.order.total_cost);
            update_cost(this.section.find(".paid .amount"), -this.order.total_cost);
            const link = `https://www.paypal.com/unifiedtransactions/details/payment/${this.order.transaction_id}`;
            this.section.find("a.paypal").attr("href", link);
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
    note: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>, order: JQuery<HTMLElement>) {
        const order_ui = new MinimalOrderUI(order);
        super(section);
        this.order_ui = order_ui;
        this.note = section.find(".orders-note");
    }

    async fetch() {
        let orders;
        try {
            orders = await G_API.get("/api/v1/order");
            orders.orders.sort((a: Order, b: Order) => b.timestamp.localeCompare(a.timestamp));
            this.orders = orders.orders;
        } catch (error) {
            this.orders = [];
        }
        G_PUBSUB.publish("ui.show_section", { section: "orders" });
    }

    override async update() {
        this.unordered_list.empty();
        if (this.orders.length) {
            for (const order of this.orders) {
                const new_item = this.list_item.clone();
                const order_link = new_item.find("a");
                order_link.attr("href", `/user/order/${order.order_id}`);
                const date: Date = new Date(order.timestamp);
                order_link.text(date.toLocaleDateString());
                this.order_ui.unordered_list = new_item.find("ul");
                this.order_ui.order = order;
                await this.order_ui.update();
                this.unordered_list.append(new_item);
            }
            this.note.hide();
        } else {
            const logged_in = await G_API.logged_in();
            const html = logged_in ? "Found no old orders" : '<a class="login">Log in</a> to view old orders';
            this.note.html(html);
            this.note.show();
            this.note.find("a").on("click", () => {
                G_PUBSUB.publish("user.login", undefined);
            });
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
    profile_menu: DropDown = new DropDown($("#profile"));

    init() {
        this.profile_menu.init();

        G_PUBSUB.subscribe("navigate.bury_url", async (params) => {
            await this.bury_url(params.section, params.path);
        });
        G_PUBSUB.subscribe("ui.show_section", async (params) => {
            await this.show(params.section);
        });
        G_PUBSUB.subscribe("ui.update", async () => {
            await this.update_header();
        });
        G_PUBSUB.subscribe("cart.update", async () => {
            await this.update_header();
        });

        $("#socials > .login > button").on("click", () => {
            G_PUBSUB.publish("user.login", undefined);
        });

        Object.values(this.sections).forEach((section) => {
            section.init();
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

        // Login button is visible if not logged in
        $("#socials > .login").toggle(!(await G_API.logged_in()));
    }
}
