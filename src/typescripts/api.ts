import { $ } from "jquery";
import { Amplify } from "aws-amplify";
import { signInWithRedirect, fetchAuthSession } from "aws-amplify/auth";

const OUTPUTS_PATH = "/config.json";

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

import sam_outputs from "../../static/outputs.json";

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
                    userPoolId: sam_outputs.user_pool,
                    userPoolClientId: sam_outputs.user_pool_client,
                    loginWith: {
                        oauth: {
                            domain: sam_outputs.cognito_host_name,
                            scopes: ["openid"],
                            redirectSignIn: [sam_outputs.website_url],
                            redirectSignOut: [sam_outputs.website_url],
                            responseType: "code",
                        },
                    },
                },
            },
        });
    }
}
