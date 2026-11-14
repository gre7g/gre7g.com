type EventCallback<T = any> = (payload: T) => void | Promise<void>;

export class PubSub<EventMap extends Record<string, any>> {
    private listeners = new Map<keyof EventMap, Set<EventCallback>>();

    subscribe<K extends keyof EventMap>(event: K, callback: EventCallback<EventMap[K]>): () => void {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }

        const eventListeners = this.listeners.get(event)!;
        eventListeners.add(callback);

        return () => {
            eventListeners.delete(callback);
            if (eventListeners.size === 0) {
                this.listeners.delete(event);
            }
        };
    }

    publish<K extends keyof EventMap>(event: K, payload: EventMap[K]): void {
        const eventListeners = this.listeners.get(event);
        if (!eventListeners) return;

        [...eventListeners].forEach((callback) => {
            Promise.resolve()
                .then(() => callback(payload))
                .catch((error) => {
                    console.error(`Async error in listener for "${String(event)}":`, error);
                });
        });
    }

    async publish_async<K extends keyof EventMap>(event: K, payload: EventMap[K]): Promise<void> {
        const eventListeners = this.listeners.get(event);
        if (!eventListeners) return;

        const results = await Promise.allSettled([...eventListeners].map((callback) => callback(payload)));

        results.forEach((result) => {
            if (result.status === "rejected") {
                console.error(`Async error in listener for "${String(event)}":`, result.reason);
            }
        });
    }
}
