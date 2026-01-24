/**
 * Auth feature module
 *
 * This module re-exports auth-related functions from the shared API client.
 * The canonical implementation lives in @/shared/api/api.ts to maintain
 * a single source of truth for API interactions.
 */

export { getCurrentUser, login, logout, type CurrentUser } from "@/shared/api/api";

