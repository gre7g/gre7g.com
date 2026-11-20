import { $ } from "jquery";

import { G_API, G_PUBSUB } from "./main";

export class DropDown {
    static active_dropdown: DropDown | null = null;

    section: JQuery<HTMLElement>;
    requires_auth: boolean;

    constructor(section: JQuery<HTMLElement>, requires_auth = false) {
        this.section = section;
        this.requires_auth = requires_auth;
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
            if (!this.section[0].contains(event.target as Node)) {
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
        if (expanded) {
            this.close();
            return;
        }

        DropDown.active_dropdown?.close();
        button.attr("aria-expanded", "true");
        this.section.find(".drop-down").show();
        DropDown.active_dropdown = this;
    }

    close() {
        this.section.find(".drop-down").hide();
        this.section.find("button").attr("aria-expanded", "false");
        if (DropDown.active_dropdown === this) {
            DropDown.active_dropdown = null;
        }
    }

    async update_header() {
        if (!this.requires_auth) {
            return;
        }

        const logged_in = await G_API.logged_in();
        this.section.toggle(logged_in);
        if (!logged_in) {
            this.close();
        }
    }
}
