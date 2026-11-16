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
        G_PUBSUB.subscribe("ui.show_error", (params) => {
            this.show_error(params.message);
        });
    }

    show_info(message: string) {
        this.section.find("span").text(message);
        this.section.addClass("info").removeClass("error");
        setTimeout(() => {
            this.close_status(message);
        }, INFO_TIMEOUT);
    }

    show_error(message: string) {
        this.section.find("span").text(message);
        this.section.addClass("error").removeClass("info");
    }

    close_status(message: string) {
        if (this.section.find("span").text() == message) {
            this.section.hide();
        }
    }
}
