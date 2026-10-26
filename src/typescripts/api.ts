import { $ } from "jquery";
import { Amplify } from "aws-amplify";
import { signInWithRedirect, fetchAuthSession } from "aws-amplify/auth";

const PAGE_EXPIRED = 419;
const CONFIG_URL = "/config.json";

declare global {
    /**
     * Outputs from `sam deploy`, kept in a file at `/config.json`
     */
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
            headers: {
                "x-csrf-token": this.csrf_token,
                "x-guest-id": this.guest_id,
            },
            dataType: "json",
            error: (response_headers: JQuery.jqXHR, text_status: string) => {
                console.log(`Error: ${text_status}`);
            },
        };
        const session = await fetchAuthSession();
        const access_token = session.tokens?.accessToken.toString();
        if (access_token) {
            (return_value as any).headers["Authorization"] = `Bearer ${access_token}`;
        }
        return return_value;
    }

    async get(path: string) {
        let common = await this.common(path);
        return await $.ajax({
            method: "GET",
            statusCode: {
                200: (data, text_status, response_headers) => {
                    this.csrf_token = response_headers.getResponseHeader("x-csrf-token")!;
                    return data;
                },
                419: async (response_headers) => {
                    // 419 indicates that the CSRF token is invalid or expired, so let's update and try again
                    this.csrf_token = response_headers.getResponseHeader("x-csrf-token")!;
                    let common = await this.common(path);
                    return await $.ajax({
                        method: "GET",
                        success: (data) => {
                            this.csrf_token = response_headers.getResponseHeader("x-csrf-token")!;
                            return data;
                        },
                        ...common,
                    });
                },
            },
            ...common,
        });
    }
}
