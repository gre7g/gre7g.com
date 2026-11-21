import { $ } from "jquery";

import { G_PUBSUB } from "./main";

/**
 * A drop-down menu in the navigation bar (books or the profile menu).
 *
 * The section is an element containing a <button> and a .drop-down list. Only one menu is open at a time: opening
 * one publishes "ui.close_dropdowns", which every DropDown subscribes to.
 */
export class DropDown {
    section: JQuery<HTMLElement>;
    // The document-level handlers are shared by all instances, so only the first init() installs them
    private static run_once: boolean = true;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

    /**
     * Subscribe to "ui.close_dropdowns" and, for the first instance only, install document-wide handlers.
     *
     * Clicking a menu button toggles its menu, and clicking anywhere else (including a menu item) closes all menus.
     * Escape closes all menus.
     */
    init() {
        // Lets the shared click handler find this instance from the clicked button
        this.section.find("button").data("drop-down", this);

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
                if (event.key == "Escape") {
                    G_PUBSUB.publish("ui.close_dropdowns", undefined);
                    if (document.activeElement instanceof HTMLElement) {
                        document.activeElement.blur();
                    }
                }
            });
        }
    }

    /**
     * Open this menu (closing any others) or close it if it's already open.
     */
    async toggle() {
        const button = this.section.find("button");
        const expand = button.attr("aria-expanded") == "false";

        // Wait for every menu to close before opening this one, or this one would be closed too
        await G_PUBSUB.publish_async("ui.close_dropdowns", undefined);

        button.attr("aria-expanded", String(expand));
        this.section.find(".drop-down").toggle(expand);
    }

    /**
     * Close this menu.
     */
    close() {
        this.section.find(".drop-down").hide();
        this.section.find("button").attr("aria-expanded", "false");
    }
}
