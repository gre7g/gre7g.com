import { G_API, G_PRODUCTS, G_PUBSUB, G_UI } from "./main";

/**
 * A product as returned by the API.
 *
 * The same shape is used for cart entries and order line items, where quantity is the number being bought. A book
 * is a parent product whose children are its formats (ebook, paperback, etc.).
 */
export interface Product {
    name: string;
    // Plain-text description (PayPal won't show much of the HTML one)
    short_desc: string;
    // HTML description
    description: string;
    // URL path of the product's listing page, e.g. "/shop/books/skeleton-crew"
    listing_path: string;
    product_id: string;
    quantity: number;
    cost_per: number;
    // Image URLs; the first is used as the thumbnail in product lists
    images: string[];
    // Download file name -> URL (order line items only)
    downloads: Record<string, string>;
    // Format, e.g. "ebook" or "paperback"
    media: string;
    status: "available" | "sold_out" | "ordered" | "canceled" | "shipped" | "partial" | "downloaded" | "refunded";
    parent_id: string | null;
    child_ids: string[];
}

/**
 * The product catalog, keyed by listing path.
 */
export class Products {
    product_list: Record<string, Product> = {};

    /**
     * Fetch all products from the API.
     */
    async load() {
        const response = await G_API.get("/api/v1/products");
        G_PRODUCTS.product_list = Object.fromEntries(
            response.products.map((product: Product) => [product.listing_path, product]),
        );
    }

    /**
     * Check whether a URL path is a product listing.
     *
     * @param path    URL path
     * @returns       True if a product has this listing path
     */
    has_path(path: string): boolean {
        return path in this.product_list;
    }

    /**
     * Show the listing page for the product at a URL path.
     *
     * @param path    URL path of a product (check with has_path() first)
     */
    async show_path(path: string): Promise<void> {
        G_UI.sections.product.product = this.product_list[path];
        G_PUBSUB.publish("ui.show_section", { section: "product" });
    }

    /**
     * Look up a product by its ID.
     *
     * @param id      Product ID
     * @returns       The product, or null if there is none with that ID
     */
    find_by_id(id: string): Product | null {
        return Object.values(this.product_list).find((product) => product.product_id === id) || null;
    }
}
