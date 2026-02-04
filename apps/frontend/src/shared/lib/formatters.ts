/**
 * Common formatting utilities for dates, errors, and display values.
 */

/**
 * Formats an error for display to the user.
 * Handles various error shapes (string, Error, object with message).
 */
export function formatError(error: unknown): string {
    if (!error) {
        return "Error inesperado.";
    }
    if (typeof error === "string") {
        return error;
    }
    if (typeof error === "object" && "message" in error) {
        return String((error as { message?: string }).message || "Error inesperado.");
    }
    return "Error inesperado.";
}

/**
 * Formats a date string for display in Spanish (Argentina) locale.
 * Returns "Sin fecha" if the value is null/undefined or invalid.
 */
export function formatDate(value?: string | null): string {
    if (!value) {
        return "Sin fecha";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString("es-AR", {
        dateStyle: "medium",
        timeStyle: "short",
    });
}

/**
 * Truncates a UUID or long string for display, showing first N characters.
 */
export function truncateId(id: string, length = 8): string {
    if (id.length <= length) {
        return id;
    }
    return `${id.substring(0, length)}...`;
}
