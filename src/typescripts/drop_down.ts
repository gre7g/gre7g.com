import { $ } from "jquery";

import { G_PUBSUB } from "./main";

export class DropDown {
    section: JQuery<HTMLElement>;
    private static run_once: boolean = true;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

    init() {
        const button = this.section.find("button");
        button.data("drop-down", this);

        G_PUBSUB.subscribe("ui.close_dropdowns", () => {
            this.close();
        });

        if (DropDown.run_once) {
            DropDown.run_once = false;

            $(document).on("click", async (event) => {
                const obj = $(event.target).data("drop-down");
                if (obj) {
                    await obj.toggle();
                } else {
                    G_PUBSUB.publish("ui.close_dropdowns", undefined);
                }
            });

            $(document).on("keydown", (event) => {
                if (event.key == "Escape" && button.attr("aria-expanded") == "true") {
                    G_PUBSUB.publish("ui.close_dropdowns", undefined);
                    if (document.activeElement instanceof HTMLElement) {
                        document.activeElement.blur();
                    }
                }
            });
        }
    }

    async toggle() {
        const button = this.section.find("button");
        const expand = button.attr("aria-expanded") == "false";

        await G_PUBSUB.publish_async("ui.close_dropdowns", undefined);

        button.attr("aria-expanded", String(expand));
        this.section.find(".drop-down").toggle(expand);
    }

    close() {
        this.section.find(".drop-down").hide();
        this.section.find("button").attr("aria-expanded", "false");
    }
}
