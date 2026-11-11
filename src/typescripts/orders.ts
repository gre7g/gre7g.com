import { Product } from "./products";

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
