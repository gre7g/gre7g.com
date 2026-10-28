import { G_UI } from "./main"

export interface Product {
    name: string;
    description: string;
    listing_path: string;
    product_id: string;
    quantity: number;
    cost_per: number;
    images: string[];
    downloads: string[];
    media: string;
    status: "available" | "sold_out" | "ordered" | "canceled" | "shipped" | "partial" | "downloaded" | "refunded";
    parent_id: string | null;
    child_ids: string[];
}

export class Products {
    product_list: Record<string, Product> = {};

    has_path(path: string): boolean {
        console.log(path, path in this.product_list);
        return path in this.product_list;
    }

    async show_path(path: string): Promise<void> {
        G_UI.sections.product.product = this.product_list[path];
        await G_UI.show("product");
    }
}
