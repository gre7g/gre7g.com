import { $ } from "jquery";

import { G_API, G_PUBSUB } from "./main";

// Constants:
// Example address shown as the e-mail placeholder when the user isn't logged in
const DEFAULT_EMAIL = "john.smith@gmail.com";

/**
 * The contact form (#contact) for sending the site owner a message.
 *
 * Send is disabled until a name and message are entered. Subscribes to "ui.update".
 */
export class Contact {
    section: JQuery<HTMLElement>;
    name: JQuery<HTMLElement>;
    email: JQuery<HTMLElement>;
    message: JQuery<HTMLElement>;
    button: JQuery<HTMLElement>;

    constructor(section: JQuery<HTMLElement>) {
        this.section = section;
        this.name = section.find(".name");
        this.email = section.find(".email");
        this.message = section.find(".message");
        this.button = section.find("button");
    }

    /**
     * Subscribe to "ui.update" and hook up the form fields and button.
     */
    init() {
        G_PUBSUB.subscribe("ui.update", async () => {
            await this.update();
        });
        this.button.on("click", async () => {
            await this.submit();
        });
        this.name.on("change", async () => {
            await this.update();
        });
        this.message.on("input", async () => {
            await this.update();
        });
    }

    /**
     * Update the e-mail placeholder for the login state and enable Send if the required fields are filled in.
     *
     * Logged-in users are told their address on file will be used if they leave the e-mail field blank.
     */
    async update() {
        const placeholder = (await G_API.logged_in()) ? "address on file" : DEFAULT_EMAIL;
        this.email.attr("placeholder", placeholder);
        this.button.prop("disabled", !(this.name.val() && this.message.val()));
    }

    /**
     * Send the message through the API, then clear the form or show an error.
     */
    async submit() {
        const name = this.name.val();
        const email = this.email.val();
        const message = this.message.val();
        if (name && message) {
            try {
                await G_API.post("/api/v1/contact", { name, email, message });
                G_PUBSUB.publish("ui.show_info", { message: "Thank you for leaving me a comment!" });
                this.name.val("");
                this.email.val("");
                this.message.val("");
            } catch (error) {
                const message = error instanceof Error ? error.message : "Unable to leave a comment";
                G_PUBSUB.publish("ui.show_error", { message });
            }
        }
    }
}
