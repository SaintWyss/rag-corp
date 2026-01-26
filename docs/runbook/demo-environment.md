# Demo Environment & Role Testing Runbook

Use this guide to spin up a fully provisioned local demo environment and manually verify the Admin vs Employee separation.

## 1. Quick Start (Spin up Stack)

To start the full stack (Frontend, Backend, DB, MinIO, Redis):

```bash
pnpm stack:full
```

_Note: This runs `docker compose --profile full up -d --build`._

## 2. Enable Demo Users (Seeding)

The backend creates demo users automatically if `DEV_SEED_DEMO=1` is set in your environment.

1.  Edit `.env` (or ensure variables are set):
    ```bash
    APP_ENV=local
    DEV_SEED_DEMO=1
    ```
2.  Restart the backend if it was already running:
    ```bash
    docker compose restart rag-api
    ```

**Logs Verification:**
Look for these lines in `docker compose logs rag-api`:

```
INFO: ... Dev seed demo: Starting provisioning...
INFO: ... Dev seed demo: Created user admin@local (admin)
INFO: ... Dev seed demo: Created user employee1@local (employee)
```

## 3. Credentials & Access

| Role         | Email             | Password    | Intended Portal     | URL            |
| :----------- | :---------------- | :---------- | :------------------ | :------------- |
| **Admin**    | `admin@local`     | `admin`     | **Admin Console**   | `/admin/users` |
| **Employee** | `employee1@local` | `employee1` | **Employee Portal** | `/workspaces`  |
| **Employee** | `employee2@local` | `employee2` | **Employee Portal** | `/workspaces`  |

## 4. Manual Verification Checklist (Role Separation)

Perform these 5 steps to sign-off on role separation:

1.  **[ ] Admin Login**:
    - Log in as `admin@local`.
    - Verify landing page is `/admin/users` (Admin Console).
    - Verify you see "Users" and "Workspaces" navigation items.
2.  **[ ] Admin Segregation**:
    - While logged in as Admin, manually change URL to `/workspaces`.
    - **Expectation**: You are forcibly redirected back to `/admin/users`.
3.  **[ ] Employee Login**:
    - Log out and log in as `employee1@local`.
    - Verify landing page is `/workspaces` (Employee Portal).
    - Verify you **do not** see "Users" or "System" links.
4.  **[ ] Employee Segregation**:
    - While logged in as Employee, manually change URL to `/admin/users`.
    - **Expectation**: You are forcibly redirected back to `/workspaces`.
5.  **[ ] Data Isolation (Cross-Access)**:
    - As Admin, ensure `employee2` has a private workspace ("Employee2 Workspace").
    - Log in as `employee1`.
    - Verify "Employee2 Workspace" is **NOT** visible in the workspace selector.
    - (Optional) Try `curl` or direct URL access to Employee2's workspace ID; ensure 403 Forbidden.

## Safety Guards

- **ENV check**: Seed logic only runs if `APP_ENV=local`.
- **Middleware**: The frontend middleware (`isWrongPortal`) handles the redirections.
- **Backend**: The `ListWorkspacesUseCase` enforces the "Owner Only" visibility at the database level.
