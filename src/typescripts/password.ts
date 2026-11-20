// Constants:
const MIN_LENGTH = 8;
const PASSWORD_CHECK = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[\^$*.\[\]{}()?\-"!@#%&/\\,><':;|_~`=])\S{8,256}$/;

export interface PasswordStatus {
    strength: number;
    sufficient: boolean;
    message: string;
}

export function check_password(new_password: string, repeat_password: string): PasswordStatus {
    const strength = Math.min(new_password.length, 20);
    if (!new_password && !repeat_password) {
        return { strength: 0, sufficient: false, message: "" };
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
