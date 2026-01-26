# Demo Environment Setup

Use this guide to spin up a fully provisioned local demo environment with Admin and Employee users pre-configured.

## Overview

The backend supports a `DEV_SEED_DEMO` flag that, when enabled in a LOCAL environment, auto-provisions:

- **Admin User**: `admin@local` (pass: `admin`)
- **Employee 1**: `employee1@local` (pass: `employee1`)
- **Employee 2**: `employee2@local` (pass: `employee2`)
- **Workspaces**:
  - "Admin Workspace" (Owner: Admin)
  - "Employee1 Workspace" (Owner: Employee 1)
  - "Employee2 Workspace" (Owner: Employee 2)

This allows you to test Admin Console features and Employee Portal isolation immediately after startup.

## Prerequisites

- Local Docker environment running
- `APP_ENV=local` (Default in `.env`)

## How to Enable

1. Open your `.env` file (root of the repo).
2. Set `DEV_SEED_DEMO=1`.

```bash
# .env
DEV_SEED_DEMO=1
```

3. Restart the backend container.

```bash
pnpm docker:up
# or just restart backend
docker compose restart backend
```

4. Verify in logs:
   ```
   backend-1  | INFO: ... Dev seed demo: Starting provisioning...
   backend-1  | INFO: ... Dev seed demo: Created user admin@local (admin)
   backend-1  | INFO: ... Dev seed demo: Created user employee1@local (employee)
   backend-1  | INFO: ... Dev seed demo: Created workspace 'Employee1 Workspace'
   ...
   ```

## Login Credentials

| Role         | Email             | Password    |
| ------------ | ----------------- | ----------- |
| **Admin**    | `admin@local`     | `admin`     |
| **Employee** | `employee1@local` | `employee1` |
| **Employee** | `employee2@local` | `employee2` |

## Safety Checks

- The seed logic STRICTLY requires `APP_ENV=local`.
- If you try to enable this in production (or any other env), the container will crash on startup (Fail-Fast) with a fatal error.
