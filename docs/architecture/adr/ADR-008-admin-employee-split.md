# ADR-008: Split Admin/Employee + Owner-Only Employees

**Status:** Proposed  
**Date:** 2026-01-25  
**Authors:** Development Team

## Context

RAG Corp has two user roles: **Admin** and **Employee**. Currently, the authorization logic is scattered:

1. **Frontend middleware** (`apps/frontend/middleware.ts` L31-35) protects `/admin/*` routes but only checks for authentication, not role.
2. **Backend endpoints** use a mix of `require_admin()` and `require_employee_or_admin()` decorators.
3. **Workspace policy** (`apps/backend/app/domain/workspace_policy.py` L41-84) implements owner-only logic, but `ListWorkspacesUseCase` fetches ALL workspaces and filters in memory for employees.
4. **UI pages** like `/admin/users` check role at runtime and show "Acceso restringido," but the page still loads.

This leads to:

- Employees potentially seeing admin routes before client-side redirect.
- Inefficient workspace listing for employees in large deployments.
- No clear separation of admin console vs employee portal.

## Decision

We will implement a **clean Admin/Employee split** with the following model:

### 1. Route Segmentation

- **Admin-only Console:** `/admin/*` (users, workspace assignment, audit logs)
- **Employee-only Portal:** `/workspaces/*` (own workspaces, documents, chat)

### 2. Frontend Middleware Enhancement

The middleware will decode the JWT to extract `role` and:

- Redirect employees accessing `/admin/*` to `/workspaces`.
- Allow admins access to all routes.

### 3. Owner-Only for Employees

- **Workspaces:** Employees see ONLY workspaces where `owner_user_id = self.user_id` (or shared via ACL).
- **Create:** Employees cannot assign `owner_user_id` to another user; it defaults to `self.user_id`.
- **Admin override:** Admins can create/assign workspaces to any user via `/admin/workspaces/{id}/assign`.

### 4. Backend Changes

- `ListWorkspacesUseCase`: For employees, pass `owner_user_id=actor.user_id` directly to the repository query instead of filtering in memory.
- `CreateWorkspaceUseCase`: Ignore `owner_user_id` from request if actor is employee.
- Move `/auth/users*` endpoints to `/admin/users*` for semantic clarity.

### 5. API Contract

- New endpoint: `POST /admin/workspaces/{workspace_id}/assign` (admin assigns owner).
- Deprecate `owner_user_id` field in `POST /v1/workspaces` request body for employee callers.

## Consequences

### Positive

- Clear separation of concerns between admin and employee flows.
- Performance improvement for employee workspace listing (DB-level filter).
- Security hardening: role check at middleware level, not page level.
- Consistent authorization model across frontend and backend.

### Negative

- Migration effort for existing frontend pages.
- Additional middleware logic to decode JWT.
- Need to update e2e tests for both roles.

## Implementation Phases

| Phase | Scope                                 | Files impacted                                              |
| ----- | ------------------------------------- | ----------------------------------------------------------- |
| P1    | FE Middleware role check              | `apps/frontend/middleware.ts`                               |
| P2    | FE Admin workspaces page              | New: `apps/frontend/app/(app)/admin/workspaces/`            |
| P3    | FE Employee page simplification       | `apps/frontend/app/(app)/workspaces/page.tsx`               |
| P4    | BE ListWorkspacesUseCase optimization | `apps/backend/app/application/usecases/workspace/list_workspaces.py`  |
| P5    | BE CreateWorkspace owner override     | `apps/backend/app/application/usecases/workspace/create_workspace.py` |
| P6    | BE Route reorganization               | `apps/backend/app/api/auth_routes.py`                       |
| P7    | BE Admin assign endpoint              | New route                                                   |
| P8    | E2E Tests                             | `tests/e2e/tests/`                                          |
| P9    | Docs (this ADR)                       | `docs/architecture/decisions/`                              |
| P10   | OpenAPI regeneration                  | `shared/contracts/`                                         |

## References

- `apps/frontend/middleware.ts` (L14-63): Current middleware logic
- `apps/backend/app/domain/workspace_policy.py` (L41-84): Owner-only policy
- `apps/backend/app/application/usecases/workspace/list_workspaces.py` (L38-69): Current listing logic
- `apps/backend/app/identity/dual_auth.py` (L167-174): Role decorators
- `apps/backend/app/api/auth_routes.py` (L162-218): Admin-only endpoints
