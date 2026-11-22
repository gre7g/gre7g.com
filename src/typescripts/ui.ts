import { $ } from "jquery";

import { Carousel } from "./carousel";
import { G_API, G_CART, G_PRODUCTS, G_PUBSUB, G_UI } from "./main";
import { Order, has_physical } from "./orders";
import { check_password, PasswordStatus } from "./password";
import { Product } from "./products";
import { DropDown } from "./drop_down";

/**
 * Format a number as US dollars and put it in an element.
 *
 * @param select  Element to update
 * @param cost    Amount in dollars
 */
function update_cost(select: JQuery<HTMLElement>, cost: number) {
    const currency = new Intl.NumberFormat("default", {
        style: "currency",
        currency: "USD",
    }).format(cost);
    select.text(currency);
}

/**
 * Base class for a page section. On its own it's used for static sections that need no code.
 *
 * Subclasses override init() for one-time setup and update() to render the section each time it's shown.
 */
class InertSection {
    section: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

    init() {}
    update() {}
}

/**
 * A section built around a list.
 *
 * The first <li> in the HTML is a template: it's removed from the page and cloned for each item when rendering.
 */
class ListSection extends InertSection {
    unordered_list: JQuery<HTMLElement>;
    list_item: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        super(section);
        this.unordered_list = section.find("ul");
        // Detaches every <li> in the section, nested ones included, so a nested list's template has to be detached
        // first (see OrderUI and OrdersUI)
        this.list_item = section.find("li").detach();
    }
}

/**
 * The product grid (#products). Lists every top-level product (formats of a book are left out).
 */
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

/**
 * The shop page (#shop). Same product grid as ProductsUI.
 */
class ShopUI extends ProductsUI {}

/**
 * The product listing page (#product-listing).
 *
 * Shows the product's images, name, price, and description. A product with formats (children) shows links to
 * them in place of an Add to Cart button.
 */
class ProductUI extends InertSection {
    // Product to show; set by Products.show_path() before the section is shown
    product: Product | null = null;
    carousel: Carousel;

    constructor(section: JQuery<HTMLElement>, example: JQuery<HTMLElement>, views: JQuery<HTMLElement>) {
        super(section);
        this.carousel = new Carousel(example, views);
    }

    /**
     * Set up the carousel and hook up the Add to Cart button.
     */
    override init() {
        this.carousel.init();
        this.section.find("button").on("click", () => {
            this.add_to_cart();
        });
    }

    /**
     * Add the product being shown to the cart.
     */
    add_to_cart() {
        if (G_UI.sections.product.product) {
            G_PUBSUB.publish("cart.add", { product: G_UI.sections.product.product });
        }
    }

    /**
     * Format the price for display.
     *
     * @returns    The cost, or for a product with formats, "from" the cheapest format's cost
     */
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

    /**
     * Build links to the product's formats.
     *
     * @returns    HTML such as '<a>ebook</a>, <a>paperback</a>, and <a>audiobook</a>', or "" if there are none
     */
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
        this.carousel.images = this.product?.images ?? [];
        this.carousel.update();
        const button = this.section.find("button");
        button.toggle(this.product?.child_ids.length == 0);
        button.text(this.product?.quantity ? "Add to Cart" : "Out of Stock");
        button.prop("disabled", !this.product?.quantity);
        $("#price").text(this.price());
        this.section.find(".product-name").text(this.product?.name!);
        let description: string = this.product?.description!;
        // A format's description is appended to its book's description
        if (this.product?.parent_id) {
            description = G_PRODUCTS.find_by_id(this.product.parent_id)?.description + description;
        }
        this.section.find(".description").html(description!);
        const media = this.media_links();
        $("#add-to-cart").toggle(media == "");
        const media_element = this.section.find(".media");
        media_element.toggle(media != "");
        media_element.find("span").html(media);
    }
}

/**
 * The cart page (#cart). Lists the cart contents with quantity inputs, extended costs, and remove buttons.
 *
 * Subscribes to "cart.update_qty" and "cart.update".
 */
class CartUI extends ListSection {
    override init() {
        G_PUBSUB.subscribe("cart.update_qty", async (params) => {
            this.update_qty(params.product_index, params.quantity);
        });
        G_PUBSUB.subscribe("cart.update", async () => {
            await this.update();
        });
    }

    /**
     * Show the new extended cost of a cart entry after its quantity changes.
     *
     * @param product_index   Index into the cart contents
     * @param quantity        New quantity
     */
    update_qty(product_index: number, quantity: number) {
        const select = this.section.find(`li:nth-child(${product_index + 1}) .ext-cost`);
        update_cost(select, G_CART.contents[product_index].cost_per * quantity);
    }

    override async update() {
        this.unordered_list.empty();
        let subtotal = 0.0;
        for (const [index, product] of G_CART.contents.entries()) {
            const new_item = this.list_item.clone();
            // Each <li> remembers its index so its input and button handlers know which entry they're for
            new_item.data("product_index", index);
            const name = new_item.find(".product-name");
            name.text(product.name);
            name.attr("href", product.listing_path);
            const quantity = new_item.find("input");
            quantity.val(product.quantity);
            quantity.on("input", function () {
                const input = $(this);
                const product_index = input.closest("li").data("product_index");
                G_PUBSUB.publish("cart.update_qty", { product_index, quantity: parseInt(input.val() ?? "0", 10) });
            });
            const item_cost = product.cost_per * product.quantity;
            subtotal += item_cost;
            update_cost(new_item.find(".ext-cost"), item_cost);
            new_item.find("button").on("click", function () {
                const product_index = $(this).closest("li").data("product_index");
                G_PUBSUB.publish("cart.delete", { product_index });
            });
            this.unordered_list.append(new_item);
        }
        this.section.find(".summary").toggle(G_CART.contents.length);
        update_cost(this.section.find(".subtotal .amount"), subtotal);
    }
}

/**
 * The checkout page (#checkout).
 *
 * Lists the cart like CartUI, then fetches shipping from the API and shows the subtotal, shipping, and total. It
 * also asks the user to log in, or requires it (for digital downloads), depending on what the API says.
 */
export class CheckoutUI extends CartUI {
    // Order total in dollars; PayPal shows it with the buttons
    total = 0.0;

    /**
     * Hook up the login button. (Doesn't subscribe to the cart events like CartUI does.)
     */
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
        const response = await G_API.post("/api/v1/cart/shipping", {}, true);
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

/**
 * The list of download links for one product in an order.
 *
 * OrderUI points unordered_list at the product's list before each update().
 */
class DownloadsUI extends ListSection {
    // File name -> URL
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

/**
 * The order details page (#order): line items with downloads, totals, and a link to the PayPal transaction.
 */
class OrderUI extends ListSection {
    // Order to show; set before the section is shown
    order: Order | null = null;
    downloads: DownloadsUI;

    constructor(section: JQuery<HTMLElement>, downloads: JQuery<HTMLElement>) {
        // Created before super() so it can grab the downloads template <li> before ListSection detaches it
        const downloads_ui = new DownloadsUI(downloads);
        super(section);
        this.downloads = downloads_ui;
    }

    override async update() {
        this.section.find(".available").toggle(!!this.order);
        this.section.find(".order-note").toggle(!this.order);
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

/**
 * The product names in one order on the orders page.
 *
 * OrdersUI points unordered_list at the order's list before each update().
 */
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

/**
 * The order history page (#orders). Lists past orders, newest first, with links to their details.
 *
 * If there are none, shows a note saying so, or asking the user to log in if they aren't.
 */
class OrdersUI extends ListSection {
    orders: Order[] = [];
    order_ui: MinimalOrderUI;
    note: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>, order: JQuery<HTMLElement>) {
        // Created before super() so it can grab the product template <li> before ListSection detaches it
        const order_ui = new MinimalOrderUI(order);
        super(section);
        this.order_ui = order_ui;
        this.note = section.find(".orders-note");
    }

    /**
     * Fetch the user's orders from the API and show the orders page. On error, show no orders.
     */
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

/**
 * The thank-you page (#thank-you). Like the order details page, plus a message about what happens next.
 */
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

/**
 * The change password page (#edit-password).
 *
 * Checks the new password as it's typed, and enables Save only when it's acceptable and both entries match. The
 * fields are cleared whenever the user navigates.
 */
class Password extends InertSection {
    old_password: JQuery<HTMLElement>;
    new_password: JQuery<HTMLElement>;
    meter: JQuery<HTMLElement>;
    repeat_password: JQuery<HTMLElement>;

    constructor(
        section: JQuery<HTMLElement>,
        old_password: JQuery<HTMLElement>,
        new_password: JQuery<HTMLElement>,
        meter: JQuery<HTMLElement>,
        repeat_password: JQuery<HTMLElement>,
    ) {
        super(section);

        this.old_password = old_password;
        this.new_password = new_password;
        this.meter = meter;
        this.repeat_password = repeat_password;
    }

    /**
     * Clear the form on navigation, check the password as it's typed, and hook up Save.
     */
    override init() {
        G_PUBSUB.subscribe("navigate.go", () => {
            this.reset();
        });
        G_PUBSUB.subscribe("navigate.bury_url", () => {
            this.reset();
        });
        this.new_password.on("input", () => {
            this.update();
        });
        this.repeat_password.on("input", () => {
            this.update();
        });
        this.section.find("button").on("click", async () => {
            await G_API.update_password(String(this.old_password.val() ?? ""), String(this.new_password.val() ?? ""));
            this.reset();
            this.set_status({ strength: 0, sufficient: false, message: "Password updated" });
        });
    }

    /**
     * Clear all the fields and the status.
     */
    reset() {
        this.old_password.val("");
        this.new_password.val("");
        this.repeat_password.val("");
        this.update();
    }

    /**
     * Show a password check result.
     *
     * @param status  Strength for the meter, whether Save is enabled, and the message to show
     */
    set_status(status: PasswordStatus) {
        this.meter.attr("value", status.strength);
        this.section.find("button").prop("disabled", !status.sufficient);
        this.section.find(".message").text(status.message);
    }

    /**
     * Check the passwords that have been entered and show the result.
     */
    override update() {
        super.update();
        const new_password = String(this.new_password.val() ?? "");
        const repeat_password = String(this.repeat_password.val() ?? "");
        this.set_status(check_password(new_password, repeat_password));
    }
}

/**
 * All the page sections and the header controls.
 *
 * Only one section is shown at a time; showing one calls its update() to render it. Subscribes to
 * "navigate.bury_url", "ui.show_section", "ui.update", and "cart.update".
 */
export class UI {
    // Key into sections of the section being shown
    current_section = "products";
    // Keys here are the section names used by "ui.show_section"
    sections = {
        about: new InertSection($("#about")),
        ai: new InertSection($("#ai")),
        appearances: new InertSection($("#appearances")),
        cart: new CartUI($("#cart")),
        checkout: new CheckoutUI($("#checkout")),
        contact: new InertSection($("#contact")),
        order: new OrderUI($("#order"), $("#order .downloads")),
        orders: new OrdersUI($("#orders"), $("#orders .products")),
        password: new Password(
            $("#edit-password"),
            $("#old-password"),
            $("#new-password"),
            $("#strength"),
            $("#repeat"),
        ),
        privacy: new InertSection($("#privacy")),
        product: new ProductUI($("#product-listing"), $("#example"), $("#views")),
        products: new ProductsUI($("#products")),
        shop: new ShopUI($("#shop")),
        sitemap: new InertSection($("#sitemap")),
        thank_you: new ThankYou($("#thank-you"), $("#thank-you .downloads")),
    };
    books_menu: DropDown = new DropDown($("#books"));
    profile_menu: DropDown = new DropDown($("#profile"));

    /**
     * Set up the menus and every section, and subscribe to the UI events.
     */
    init() {
        this.books_menu.init();
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

    /**
     * Show one section, hide the rest, and render the one being shown.
     *
     * @param section     Key into sections
     */
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

    /**
     * Update the cart count and show either the login button or the profile menu.
     */
    async update_header() {
        // Shopping cart contents
        $("#cart_button a").text(G_CART.contents.length == 0 ? "" : G_CART.contents.length);

        // Login button or profile menu is visible depending on whether the user is logged in
        const logged_in = await G_API.logged_in();
        this.profile_menu.section.toggle(logged_in);
        $("#socials > .login").toggle(!logged_in);
    }
}
