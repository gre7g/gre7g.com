import { $ } from "jquery";
import { Amplify } from "aws-amplify";
import { signInWithRedirect, fetchAuthSession } from "aws-amplify/auth";

import { G_SAM_OUTPUTS } from "./main";

/**
 * The Api class handles authentication, AJAX requests to the API, CSRF tokens, and request retries.
 */
export class Api {
    csrf_token: string = "";
    guest_id: string = "";

    load() {
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
                            redirectSignIn: [G_SAM_OUTPUTS.website_url],
                            redirectSignOut: [G_SAM_OUTPUTS.website_url],
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
            return await $.ajax({ method: "GET", success: success, ...common });
        };
        return await $.ajax({ method: method, statusCode: { 200: success, 419: page_expired }, ...common });
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
