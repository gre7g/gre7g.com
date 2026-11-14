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
        const status = this.section.find(".message");
        if (name && message) {
            try {
                await G_API.post("/api/v1/contact", { name, email, message });
                status.text("Thank you for leaving me a comment!");
            } catch (error) {
                if (error instanceof Error) {
                    status.text(error.message);
                } else {
                    status.text("Unable to leave comment");
                }
            }
        }
    }
}
