import { $ } from "jquery";
import { Amplify } from "aws-amplify";
import { signInWithRedirect, fetchAuthSession } from "aws-amplify/auth";

const CONFIG_URL = "/config.json";

interface SamOutputs {
    api_endpoint: string;
    audit_log: string;
    carts_table_name: string;
    cognito_host_name: string;
    cognito_login_url: string;
    orders_table_name: string;
    products_table_name: string;
    user_pool: string;
    user_pool_client: string;
    web_distribution: string;
    web_file_storage: string;
    website_url: string;
}

const response: Response = await fetch(CONFIG_URL);
const SAM_OUTPUTS: SamOutputs = await response.json();

/**
 * The Api class handles authentication, AJAX requests to the API, CSRF tokens, and request retries.
 */
export class Api {
    csrf_token: string = "";
    guest_id: string = "";

    constructor() {
        // Configure Amplify
        Amplify.configure({
            Auth: {
                Cognito: {
                    userPoolId: SAM_OUTPUTS.user_pool,
                    userPoolClientId: SAM_OUTPUTS.user_pool_client,
                    loginWith: {
                        oauth: {
                            domain: SAM_OUTPUTS.cognito_host_name,
                            scopes: ["openid"],
                            redirectSignIn: [SAM_OUTPUTS.website_url],
                            redirectSignOut: [SAM_OUTPUTS.website_url],
                            responseType: "code",
                        },
                    },
                },
            },
        });
    }

    private async common(path: string): Promise<Record<string, any>> {
        let return_value = {
            url: path,
            contentType: "application/json",
            dataType: "json",
            headers: {
                "x-csrf-token": this.csrf_token,
                "x-guest-id": this.guest_id,
            },
            error: (response_headers: JQuery.jqXHR, text_status: string) => {
                throw new Error(text_status); // TODO
            },
        };
        const session = await fetchAuthSession();
        const access_token = session.tokens?.accessToken.toString();
        if (access_token) {
            (return_value as any).headers["Authorization"] = `Bearer ${access_token}`;
        }
        return return_value;
    }

    private async request(method: string, path: string, data?: Record<string, any>) {
        let common = await this.common(path);
        if (data) {
            common.data = JSON.stringify(data);
        }
        const success = (response, text_status, response_headers) => {
            this.csrf_token = response_headers.getResponseHeader("x-csrf-token")!;
            return response;
        };
        const page_expired = async (response_headers) => {
                // 419 indicates that the CSRF token is invalid or expired, so let's update and try again
                this.csrf_token = response_headers.getResponseHeader("x-csrf-token")!;
                common = await this.common(path);
                if (data) {
                    common.data = data;
                }
                return await $.ajax({method: "GET", success: success, ...common});
            };
        return await $.ajax({method: method, statusCode: {200: success, 419: page_expired}, ...common});
    }

    async get(path: string) {
        return await this.request("GET", path);
    }

    async post(path: string, data: Record<string, any>) {
        return await this.request("POST", path, data);
    }

    async put(path: string, data: Record<string, any>) {
        return await this.request("PUT", path, data);
    }

    async delete(path: string, data: Record<string, any>) {
        return await this.request("DELETE", path, data);
    }
}
