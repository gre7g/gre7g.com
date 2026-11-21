// A subscriber may be synchronous or asynchronous.
type EventCallback<T = any> = (payload: T) => void | Promise<void>;

/**
 * A minimal, type-safe publish/subscribe event bus.
 *
 * EventMap maps event names to payload types (see the Events interface in main.ts), so publishing an event with the
 * wrong payload, or subscribing with a callback of the wrong type is a compile error.
 */
export class PubSub<EventMap extends Record<string, any>> {
    // Each event has a set of callbacks; events with no subscribers are removed from the map
    private listeners = new Map<keyof EventMap, Set<EventCallback>>();

    /**
     * Register a callback for an event.
     *
     * @param event       Event name
     * @param callback    Function called with the event's payload each time the event is published
     * @returns           Function that unsubscribes the callback
     */
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

    /**
     * Publish an event without waiting for subscribers (fire and forget).
     *
     * Each callback runs in its own microtask, so publish() returns before any of them have run. Errors (thrown or
     * rejected) are logged to the console rather than propagated to the publisher.
     *
     * @param event       Event name
     * @param payload     Data passed to every subscriber
     */
    publish<K extends keyof EventMap>(event: K, payload: EventMap[K]): void {
        const eventListeners = this.listeners.get(event);
        if (!eventListeners) return;

        // Copy the set so callbacks that subscribe/unsubscribe don't affect this loop. Wrapping each call in
        // Promise.resolve().then() makes synchronous and asynchronous callbacks behave the same, and keeps one failing
        // callback from stopping the others.
        [...eventListeners].forEach((callback) => {
            Promise.resolve()
                .then(() => callback(payload))
                .catch((error) => {
                    console.error(`Async error in listener for "${String(event)}":`, error);
                });
        });
    }

    /**
     * Publish an event and wait until every subscriber has finished.
     *
     * Callbacks are started immediately (synchronous ones run before this returns its promise) and run concurrently.
     * Failures are logged to the console rather than propagated.
     *
     * @param event       Event name
     * @param payload     Data passed to every subscriber
     */
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
