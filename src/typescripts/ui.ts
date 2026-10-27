import { G_PRODUCTS} from "./main";

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
    constructor(section: JQuery<HTMLElement>) {
        super(section);
    }

    async update() {
        this.unordered_list.empty();
        G_PRODUCTS.product_list.forEach((product) => {
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

export class UI {
    products: ProductsUI;

    constructor() {
        this.products = new ProductsUI($("#products"));
    }
}
