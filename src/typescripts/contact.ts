import { $ } from "jquery";

import { G_API, G_PUBSUB } from "./main";

export class Contact {
    section: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
    }

    init() {
        G_PUBSUB.subscribe("ui.update", async () => {
            await this.update();
        });
        this.section.find("button").on("click", async () => {
            await this.submit();
        });
    }

    async update() {
        const placeholder = (await G_API.logged_in()) ? "address on file" : "john.smith@gmail.com";
        $("#email").attr("placeholder", placeholder);
        this.section.find(".message").text();
    }

    async submit() {
        const name = $("#name").val();
        const email = $("#email").val();
        const message = $("#message").val();
        if (name && message) {
            try {
                await G_API.post("/api/v1/contact", { name, email, message });
                G_PUBSUB.publish("ui.show_info", { message: "Thank you for leaving me a comment!" });
            } catch (error) {
                if (error instanceof Error) {
                    G_PUBSUB.publish("ui.show_error", { message: error.message });
                } else {
                    G_PUBSUB.publish("ui.show_error", { message: "Unable to leave comment" });
                }
            }
        }
    }
}
