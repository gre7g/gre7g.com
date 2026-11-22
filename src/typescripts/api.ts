import { Amplify } from "aws-amplify";
import { fetchAuthSession, signInWithRedirect, signOut, AuthSession, updatePassword } from "aws-amplify/auth";

import { G_PUBSUB, G_SAM_OUTPUTS } from "./main";

// Custom status the API returns when the CSRF token is missing, invalid, or expired
const PAGE_EXPIRED = 419;

/**
 * Stand-in for an Amplify AuthSession when dummy authentication is enabled (local testing).
 *
 * Both the access token and the user sub are set to the ?auth= value from the page URL.
 */
interface DummyAuth {
    tokens: {
        accessToken: string;
    };
    userSub: string;
}

/**
 * Authentication via Cognito (through Amplify), or a dummy implementation for local testing.
 *
 * Dummy authentication is enabled with VITE_USE_DUMMY_AUTH=true. In that mode, login, logout, and password changes
 * just show an info message, and the user is whoever is named in the ?auth= URL parameter.
 *
 * Subscribes to "user.login" and "user.logout".
 */
class AuthLayer {
    use_dummy_auth = import.meta.env.VITE_USE_DUMMY_AUTH === "true";
    // Set by Main.main() from the ?auth= URL parameter
    dummy_auth: string = "";

    /**
     * Subscribe to the login and logout events.
     */
    init() {
        G_PUBSUB.subscribe("user.login", async () => {
            await this.login();
        });
        G_PUBSUB.subscribe("user.logout", async () => {
            await this.logout();
        });
    }

    /**
     * Send the user to the Cognito hosted login page.
     */
    async login() {
        if (this.use_dummy_auth) {
            G_PUBSUB.publish("ui.show_info", { message: "No login method with dummy authentication" });
        } else {
            await signInWithRedirect();
        }
    }

    /**
     * Configure Amplify with the Cognito settings from /config.json. Not needed with dummy authentication.
     */
    load() {
        if (!this.use_dummy_auth) {
            // Configure Amplify
            Amplify.configure({
                Auth: {
                    Cognito: {
                        userPoolId: G_SAM_OUTPUTS.user_pool,
                        userPoolClientId: G_SAM_OUTPUTS.user_pool_client,
                        loginWith: {
                            oauth: {
                                domain: G_SAM_OUTPUTS.cognito_host_name,
                                scopes: ["openid"],
                                // Cognito sends the user back to /login, which Navigator handles
                                redirectSignIn: [`${G_SAM_OUTPUTS.website_url}/login`],
                                redirectSignOut: [G_SAM_OUTPUTS.website_url],
                                responseType: "code",
                            },
                        },
                    },
                },
            });
        }
    }

    /**
     * Get the current authentication session.
     *
     * @returns    The Amplify session (tokens and userSub are undefined when not logged in), or a dummy one
     */
    async get_session(): Promise<AuthSession | DummyAuth> {
        if (this.use_dummy_auth) {
            return {
                tokens: { accessToken: this.dummy_auth },
                userSub: this.dummy_auth,
            };
        } else {
            return await fetchAuthSession();
        }
    }

    /**
     * Log the user out and refresh the UI.
     */
    async logout() {
        if (this.use_dummy_auth) {
            G_PUBSUB.publish("ui.show_info", { message: "No logout method with dummy authentication" });
        } else {
            await signOut();
            G_PUBSUB.publish("ui.update", undefined);
        }
    }

    /**
     * Check whether a user is logged in.
     *
     * @returns    True if the session has a user sub
     */
    async logged_in(): Promise<boolean> {
        const auth = await this.get_session();
        return Boolean(auth.userSub);
    }

    /**
     * Change the logged-in user's password and refresh the UI.
     *
     * @param old_password    Current password
     * @param new_password    Replacement password
     */
    async update_password(old_password: string, new_password: string) {
        if (this.use_dummy_auth) {
            G_PUBSUB.publish("ui.show_info", { message: "No password update method with dummy authentication" });
        } else {
            await updatePassword({ oldPassword: old_password, newPassword: new_password });
            G_PUBSUB.publish("ui.update", undefined);
        }
    }
}

/**
 * The Api class handles authentication, AJAX requests to the API, CSRF tokens, and request retries.
 */
export class Api extends AuthLayer {
    // Latest CSRF token from the API; sent with every request and refreshed from every response
    csrf_token: string = "";
    // Identifies the guest cart; set by Cart.load()
    guest_id: string = "";

    /**
     * Make one request to the API.
     *
     * Adds the CSRF token, guest ID, and (if logged in) bearer token headers, and saves any new CSRF token the response
     * sends back.
     *
     * @param method  HTTP method
     * @param path    URL path, e.g. "/api/v1/cart"
     * @param data    Optional body, sent as JSON
     * @returns       The raw fetch() response
     */
    private async single_request(method: string, path: string, data?: Record<string, any>): Promise<Response> {
        let headers: Record<string, any> = {
            "content-type": "application/json",
            accept: "application/json",
            "x-csrf-token": this.csrf_token,
            "x-guest-id": this.guest_id,
        };
        const session = await this.get_session();
        const access_token = session.tokens?.accessToken.toString();
        if (access_token) {
            headers.authorization = `bearer ${access_token}`;
        }
        let params: Record<string, any> = { method, headers };
        if (data) {
            params.body = JSON.stringify(data);
        }
        const response = await fetch(path, params);
        const token = response.headers.get("x-csrf-token");
        if (token) {
            this.csrf_token = token;
        }
        return response;
    }

    /**
     * Make a request to the API, retrying once if the CSRF token was rejected.
     *
     * @param method  HTTP method
     * @param path    URL path, e.g. "/api/v1/cart"
     * @param data    Optional body, sent as JSON
     * @returns       The parsed JSON response
     * @throws        Error with the API's message if the response is not OK
     */
    private async request(method: string, path: string, data?: Record<string, any>) {
        let response = await this.single_request(method, path, data);
        if (response.status == PAGE_EXPIRED) {
            // The CSRF token is invalid or expired. We've updated it, so let's retry.
            response = await this.single_request(method, path, data);
        }
        const result = await response.json();
        if (response.ok) {
            return result;
        } else {
            throw new Error(result.message);
        }
    }

    /**
     * Make a request to the API, retrying once if the CSRF token was rejected. If the request fails, it publishes an
     * "ui.show_error" event and then throws an error. Even though it handles the error, we don't want the caller code
     * to proceed with bad data.
     *
     * @param method  HTTP method
     * @param path    URL path, e.g. "/api/v1/cart"
     * @param data    Optional body, sent as JSON
     * @returns       The parsed JSON response
     * @throws        Error with the API's message if the response is not OK
     */
    private async request_with_error(method: string, path: string, data?: Record<string, any>) {
        try {
            return await this.request(method, path, data);
        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            G_PUBSUB.publish("ui.show_error", { message });
            throw error;
        }
    }

    /**
     * GET from the API. See request().
     */
    async get(path: string, alert: boolean = false) {
        if (alert) {
            return await this.request_with_error("GET", path);
        } else {
            return await this.request("GET", path);
        }
    }

    /**
     * POST to the API. See request().
     */
    async post(path: string, data: Record<string, any>, alert: boolean = false) {
        if (alert) {
            return await this.request_with_error("POST", path, data);
        } else {
            return await this.request("POST", path, data);
        }
    }

    /**
     * PUT to the API. See request().
     */
    async put(path: string, data: Record<string, any>, alert: boolean = false) {
        if (alert) {
            return await this.request_with_error("PUT", path, data);
        } else {
            return await this.request("PUT", path, data);
        }
    }

    /**
     * DELETE from the API. See request().
     */
    async delete(path: string, data: Record<string, any>, alert: boolean = false) {
        if (alert) {
            return await this.request_with_error("DELETE", path, data);
        } else {
            return await this.request("DELETE", path, data);
        }
    }
}
