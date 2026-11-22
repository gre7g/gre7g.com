import { G_PUBSUB } from "./main";

// Constants:
const INFO_TIMEOUT = 60 * 1000; // One minute

/**
 * The status bar that shows info, warning, and error messages at the top of the page.
 *
 * Subscribes to "ui.show_info", "ui.show_warning", and "ui.show_error". The message type is shown with an
 * "info", "warning", or "error" class on the section, and its close button hides the bar.
 */
export class Status {
    section: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

    /**
     * Subscribe to the status events and hook up the close button.
     */
    init() {
        G_PUBSUB.subscribe("ui.show_info", (params) => {
            this.show_info(params.message);
        });
        G_PUBSUB.subscribe("ui.show_warning", (params) => {
            this.show_warning(params.message);
        });
        G_PUBSUB.subscribe("ui.show_error", (params) => {
            this.show_error(params.message);
        });
        // Pass the current text so close_status() always matches it
        this.section.find("button").on("click", () => {
            this.close_status(this.section.find("span").text());
        });
    }

    private show(message: string, cls: string) {
        this.section.show();
        this.section.find("span").text(message);
        this.section.toggleClass("info", cls === "info");
        this.section.toggleClass("warning", cls === "warning");
        this.section.toggleClass("error", cls === "error");
    }

    /**
     * Show an informational message that closes itself after INFO_TIMEOUT.
     *
     * Ignored if an error is currently showing so that errors aren't hidden by less important messages.
     *
     * @param message     Text to display
     */
    show_info(message: string) {
        // Don't replace an error or warning with a message
        if (this.section.is(":visible") && (this.section.hasClass("error") || this.section.hasClass("warning"))) {
            return;
        }
        this.show(message, "info");
        // Only closes the bar if this message is still the one showing
        setTimeout(() => {
            this.close_status(message);
        }, INFO_TIMEOUT);
    }

    /**
     * Show a warning message. Warnings stay up until closed.
     *
     * @param message     Text to display
     */
    show_warning(message: string) {
        // Don't replace an error with a warning
        if (this.section.is(":visible") && this.section.hasClass("error")) {
            return;
        }
        this.show(message, "warning");
    }

    /**
     * Show an error message. Errors stay up until closed.
     *
     * @param message     Text to display
     */
    show_error(message: string) {
        this.show(message, "error");
    }

    /**
     * Hide the status bar, but only if it is still showing the given message.
     *
     * This keeps an old message's timer from closing a newer message.
     *
     * @param message     Text of the message to close
     */
    close_status(message: string) {
        if (this.section.find("span").text() == message) {
            this.section.hide();
        }
    }
}
