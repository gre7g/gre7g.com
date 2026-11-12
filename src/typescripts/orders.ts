import { Product } from "./products";

const DIGITAL_MEDIA = ["ebook", "audiobook"];
const PHYSICAL_MEDIA = ["paperback", "jewelry"];

export interface Order {
    products: Product[];
    subtotal_cost: number;
    shipping_cost: number;
    total_cost: number;
    discount: number;
    order_id: string;
    timestamp: string;
    notes: string[];
}

export class Orders {
    orders: Order[] = [];
}

export function has_downloads(order: Order): boolean {
    return order.products.some((product) => DIGITAL_MEDIA.includes(product.media));
}

export function has_physical(order: Order): boolean {
    return order.products.some((product) => PHYSICAL_MEDIA.includes(product.media));
}
