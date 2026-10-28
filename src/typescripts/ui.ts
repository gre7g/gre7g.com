import { G_CART, G_PRODUCTS } from "./main";
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
        Object.values(G_PRODUCTS.product_list).forEach((product) => {
            if (!product.parent_id) {
                const new_item = this.list_item.clone();
                new_item.find("a").attr("href", product.listing_path);
                new_item.find("img").attr("src", product.images[0]);
                new_item.find(".product-name").text(product.name);
                new_item.find(".media").text(product.media);
                this.unordered_list.append(new_item);
            }
        });
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
            Object.values(G_PRODUCTS.product_list).forEach((product) => {
                if (this.product?.child_ids.includes(product.product_id) && product.cost_per < min_cost) {
                    min_cost = product.cost_per;
                }
            });
            return `from ${min_cost}`;
        }
    }

    private media_links(): string {
        let links: string[] = [];
        Object.values(G_PRODUCTS.product_list).forEach((product) => {
            if (this.product?.child_ids.includes(product.product_id)) {
                links.push(`<a href="${product.listing_path}">${product.media}</a>`);
            }
        });
        const formatter = new Intl.ListFormat("en", { style: "long", type: "conjunction" });
        return formatter.format(links);
    }

    async update() {
        $("#example").attr("href", this.product?.images[0]!);
        $("#price").text(this.price());
        const views = $("#views");
        this.product?.images?.forEach((path) => {
            const view = $(`<img src="${path}" />`);
            views.append(view);
        });
        this.section.find(".product-name").text(this.product?.name!);
        this.section.find(".description").html(this.product?.description!);
        const media = this.media_links();
        $("#add-to-cart").toggle(media != "");
        const media_element = this.section.find(".media");
        media_element.toggle(media != "");
        media_element.find("span").html(media);
    }
}

class CartUI extends ListSection {
    async update() {
        this.unordered_list.empty();
        Object.values(G_CART.contents).forEach((product) => {
            if (!product.parent_id) {
                const new_item = this.list_item.clone();
                new_item.find(".product-name").text(product.name);
                this.unordered_list.append(new_item);
            }
        });
    }
}

export class UI {
    current_section = "products";
    sections = {
        products: new ProductsUI($("#products")),
        product: new ProductUI($("#product-listing")),
        cart: new CartUI($("#cart")),
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
