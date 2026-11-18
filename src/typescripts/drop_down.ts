import { $ } from "jquery";

import{G_API} from "./main";
import { G_PUBSUB } from "./main";

export class DropDown {
    section: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

    init() {
        const button = this.section.find("button");
        const menu = this.section.find(".drop-down");

        G_PUBSUB.subscribe("ui.update", async () => {
            await this.update_header();
        });

        // Click the menu to toggle it
        button.on("click", () => {
            this.toggle();
        });

        // Close the menu when the user clicks a link in the menu, outside the menu, or presses the escape key
        menu.find("a").on("click", () => {
            this.close();
        });
        $(document).on("click", (event) => {
            if ($(event.target).closest("#profile").length == 0) {
                this.close();
            }
        });
        $(document).on("keydown", (event) => {
            if (event.key == "Escape" && button.attr("aria-expanded") == "true") {
                this.close();
                button.trigger("focus");
            }
        });
    }

    toggle() {
        const button = this.section.find("button");
        const expanded = button.attr("aria-expanded") == "true";
        button.attr("aria-expanded", String(!expanded));
        this.section.find(".drop-down").toggle(!expanded);
    }

    close() {
        this.section.find(".drop-down").hide();
        this.section.find("button").attr("aria-expanded", "false");
    }

    async update_header() {
        const logged_in = await G_API.logged_in();
        this.section.toggle(logged_in);
        if (!logged_in) {
            this.close();
        }
    }
}
