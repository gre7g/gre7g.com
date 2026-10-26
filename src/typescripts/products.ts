declare global { interface Product {    name: string,
    description: string,
    listing_path: string,
    product_id: string,
    quantity: number,
    cost_per: number,
    images: string[],
    downloads: string[],
    status: "available" | "sold_out" | "ordered" | "canceled" | "shipped" | "partial" | "downloaded" | "refunded",
    parent_id: string | null,
    child_ids: string[]}}

export class Products {
    product_list: Product[] = [];

    has_path(path: string): boolean {
        return this.product_list.some(item => item.listing_path === path);
    }

    async show_path(path: string): Promise<void> {
        // TODO
    }
}
