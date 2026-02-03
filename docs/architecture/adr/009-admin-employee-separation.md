# ADR-009: Admin vs Employee Separation Model

## Status

Accepted

## Context

The system supports two distinct roles: **Admin** and **Employee**.
We need a clear separation of concerns where:

1. Admins have a dedicated Console to manage users and system-wide workspaces.
2. Employees have a Portal to manage only their assigned workspaces.
3. Data isolation is enforced: Employees must never see workspaces they do not own or are not assigned to.

## Decision

We adopt a **Strict Separation Model** enforced at both Frontend (Routing) and Backend (API/Data) layers.

### 1. Frontend Route Segregation

- **Middleware**: Intercepts requests to enforce role-based portal access.
- **Admin Console**: Hosted at `/admin/*`. Accessible ONLY to users with `role=admin`.
- **Employee Portal**: Hosted at `/workspaces/*`. Accessible to all authenticated users, but optimized for Employees.
- **Redirection Logic**:
  - Authenticated Admins visiting `/workspaces` are redirected to `/admin/users` (or `/admin/workspaces`).
  - Authenticated Employees visiting `/admin` are redirected to `/workspaces`.
- **Source**: `apps/frontend/middleware.ts` (Lines 84-92 `isWrongPortal`).

### 2. Backend Access Control

- **Provisioning**: Only Admins can create (`POST`), update (`PATCH`), or archive (`DELETE`) workspaces.
  - Source: `apps/backend/app/interfaces/api/http/routes.py` (e.g., `create_workspace` uses `require_user_admin`).
- **Data Isolation**:
  - **Listing**: The `ListWorkspacesUseCase` enforces filtering at the database level.
    - If `role=admin`: Can view all or filter by specific owner.
    - If `role=employee`: `owner_user_id` is forcibly overwritten to `actor.user_id`.
    - Source: `apps/backend/app/application/usecases/list_workspaces.py` (L50-58).
- **Document Management**:
  - Employees have **Read/Write** access to documents within their permitted workspaces (e.g. `upload_workspace_document`).
  - Raw text ingestion (`ingest_workspace_text`) is currently restricted to Admins (L1468 of routes.py).

## Consequences

- **Security**: "Owner-only" policy is robustly enforced by the backend, preventing data leaks even if the frontend were bypassed.
- **UX**: Clear distinction between "managing the system" (Admin) and "doing work" (Employee).
- **Limitation**: Employees cannot create their own workspaces; they rely on Admins to provision them. This aligns with a corporate "provisioned" model.
