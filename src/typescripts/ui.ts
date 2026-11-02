import { G_API, G_CART, G_PRODUCTS } from "./main";
import { Product } from "./products";

class ListSection {
    section: JQuery<HTMLElement>;
    unordered_list: JQuery<HTMLElement>;
    list_item: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
        this.unordered_list = section.find("ul");
        this.list_item = section.find("li").detach();
    }
}

class ProductsUI extends ListSection {
    async update() {
        this.unordered_list.empty();
        const populate_item = (product: Product) => {
            if (!product.parent_id) {
                const new_item = this.list_item.clone();
                new_item.find("a").attr("href", product.listing_path);
                new_item.find("img").attr("src", product.images[0]);
                new_item.find(".product-name").text(product.name);
                new_item.find(".media").text(product.media);
                this.unordered_list.append(new_item);
            }
        };
        Object.values(G_PRODUCTS.product_list).forEach(populate_item);
    }
}

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
    async update() {
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

export class UI {
    current_section = "products";
    sections = {
        products: new ProductsUI($("#products")),
        product: new ProductUI($("#product-listing")),
        cart: new CartUI($("#cart")),
        checkout: new CheckoutUI($("#checkout")),
    };

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
}
