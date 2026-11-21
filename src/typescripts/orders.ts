import { Product } from "./products";

// Product media types that are delivered as downloads vs. shipped
const DIGITAL_MEDIA = ["ebook", "audiobook"];
const PHYSICAL_MEDIA = ["paperback", "jewelry"];

/**
 * An order as returned by the API.
 */
export interface Order {
    products: Product[];
    subtotal_cost: number;
    shipping_cost: number;
    total_cost: number;
    // PayPal transaction ID, used to link to the payment details
    transaction_id: string;
    discount: number;
    // Our order ID (not PayPal's)
    order_id: string;
    timestamp: string;
    notes: string[];
}

/**
 * Check whether an order includes any digital downloads.
 *
 * @param order   Order to check
 * @returns       True if any product is a digital medium
 */
export function has_downloads(order: Order): boolean {
    return order.products.some((product) => DIGITAL_MEDIA.includes(product.media));
}

/**
 * Check whether an order includes anything that has to be shipped.
 *
 * @param order   Order to check
 * @returns       True if any product is a physical medium
 */
export function has_physical(order: Order): boolean {
    return order.products.some((product) => PHYSICAL_MEDIA.includes(product.media));
}
