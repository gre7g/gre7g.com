import { G_PUBSUB } from "./main";

// Constants:
const INFO_TIMEOUT = 60 * 1000; // One minute

export class Status {
    section: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

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
        this.section.find("button").on("click", () => {
            this.close_status(this.section.find("span").text());
        });
    }

    show_info(message: string) {
        // Don't replace an error with a message
        if (this.section.is(":visible") && this.section.hasClass("error")) {
            return;
        }

        this.section.find("span").text(message);
        this.section.addClass("info");
        this.section.removeClass("warning");
        this.section.removeClass("error");
        setTimeout(() => {
            this.close_status(message);
        }, INFO_TIMEOUT);
    }

    show_warning(message: string) {
        this.section.find("span").text(message);
        this.section.removeClass("info");
        this.section.addClass("warning");
        this.section.removeClass("error");
    }

    show_error(message: string) {
        this.section.find("span").text(message);
        this.section.removeClass("info");
        this.section.removeClass("warning");
        this.section.addClass("error");
    }

    close_status(message: string) {
        if (this.section.find("span").text() == message) {
            this.section.hide();
        }
    }
}
