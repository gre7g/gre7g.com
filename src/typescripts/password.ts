import { G_API } from "./main";

// Constants:
const MIN_LENGTH = 8;
// Requires a lowercase letter, an uppercase letter, a digit, and a special character, and 8-256 characters with no
// whitespace
const PASSWORD_CHECK = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[\^$*.\[\]{}()?\-"!@#%&/\\,><':;|_~`=])\S{8,256}$/;

/**
 * Result of checking a new password.
 */
export interface PasswordStatus {
    // Value for the strength meter (the password length, capped at 20)
    strength: number;
    // True if the password is acceptable and the two entries match
    sufficient: boolean;
    // Explanation shown to the user, or "" if there's nothing to say
    message: string;
}

/**
 * Check a new password and its repeated entry.
 *
 * The checks are made in order (length, then character classes, then match) and the first failure is reported.
 *
 * @param new_password        Password the user typed
 * @param repeat_password     Password typed into the "repeat" field
 * @returns                   Strength, whether it's acceptable, and a message
 */
export async function check_password(new_password: string, repeat_password: string): Promise<PasswordStatus> {
    const strength = Math.min(new_password.length, 20);
    const logged_in = await G_API.logged_in();
    if (!logged_in) {
        return {
            strength: 0,
            sufficient: false,
            message: "No logged in",
        };
    }

    // Nothing typed yet, so don't nag
    if (!new_password && !repeat_password) {
        return {
            strength: 0,
            sufficient: false,
            message: "",
        };
    }
    if (new_password.length < MIN_LENGTH) {
        return {
            strength: strength,
            sufficient: false,
            message: "Too weak",
        };
    }
    if (!PASSWORD_CHECK.test(new_password)) {
        return {
            strength: strength,
            sufficient: false,
            message: "Must include an uppercase, a lower, a number, and a special character",
        };
    }
    if (new_password !== repeat_password) {
        return {
            strength: strength,
            sufficient: false,
            message: "Passwords do not match",
        };
    }
    return {
        strength: strength,
        sufficient: true,
        message: "",
    };
}
