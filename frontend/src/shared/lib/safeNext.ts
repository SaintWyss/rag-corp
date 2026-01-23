/**
 * Safe redirect helper to prevent open-redirect vulnerabilities.
 * Only allows internal paths (must start with / and not contain protocol separators).
 */

export const SAFE_DEFAULT_AFTER_LOGIN = "/workspaces";

/**
 * Sanitizes a redirect path to ensure it's safe (internal only).
 * Returns fallback if the path is invalid or potentially external.
 */
export function sanitizeNextPath(
    raw: string | null | undefined,
    fallback: string = SAFE_DEFAULT_AFTER_LOGIN
): string {
    // Empty or null -> fallback
    if (!raw || raw.trim() === "") {
        return fallback;
    }

    const trimmed = raw.trim();

    // Must start with /
    if (!trimmed.startsWith("/")) {
        return fallback;
    }

    // Reject protocol-relative URLs (//example.com)
    if (trimmed.startsWith("//")) {
        return fallback;
    }

    // Reject absolute URLs (http://, https://, etc.)
    if (trimmed.includes("://")) {
        return fallback;
    }

    // Reject backslashes (Windows path traversal, URL encoding bypass attempts)
    if (trimmed.includes("\\")) {
        return fallback;
    }

    // Reject control characters (newlines, tabs, null bytes)
    // eslint-disable-next-line no-control-regex
    if (/[\x00-\x1F\x7F]/.test(trimmed)) {
        return fallback;
    }

    // Path is safe
    return trimmed;
}
