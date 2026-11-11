import { Amplify } from "aws-amplify";
import { fetchAuthSession } from "aws-amplify/auth";

import { G_SAM_OUTPUTS } from "./main";

const PAGE_EXPIRED = 419;

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
                            redirectSignIn: [`${G_SAM_OUTPUTS.website_url}/login`],
                            redirectSignOut: [G_SAM_OUTPUTS.website_url],
                            responseType: "code",
                        },
                    },
                },
            },
        });
    }

    private async single_request(method: string, path: string, data?: Record<string, any>): Promise<Response> {
        let headers: Record<string, any> = {
            "content-type": "application/json",
            accept: "application/json",
            "x-csrf-token": this.csrf_token,
            "x-guest-id": this.guest_id,
        };
        const session = await fetchAuthSession();
        const access_token = session.tokens?.accessToken.toString();
        if (access_token) {
            headers.authorization = `bearer ${access_token}`;
        }
        let params: Record<string, any> = { method, headers };
        if (data) {
            params.data = JSON.stringify(data);
        }
        const response = await fetch(path, params);
        const token = response.headers.get("x-csrf-token");
        if (token) {
            this.csrf_token = token;
        }
        return response;
    }

    private async request(method: string, path: string, data?: Record<string, any>) {
        let response = await this.single_request(method, path, data);
        if (response.status == PAGE_EXPIRED) {
            // The CSRF token is invalid or expired. We've updated it, so let's retry.
            response = await this.single_request(method, path, data);
        }
        if (response.ok) {
            return await response.json();
        } else {
            throw new Error(response.statusText);
        }
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
