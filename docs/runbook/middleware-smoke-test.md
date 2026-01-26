# ADR-008 Middleware Smoke Test

## Prerequisites

1. Backend running (`pnpm docker:up`)
2. Frontend running (`cd apps/frontend && pnpm dev`)
3. At least one admin user and one employee user in the database

## Test Cases

### Test 1: Unauthenticated Access to Private Routes

| Step | Action                                          | Expected Result                          |
| ---- | ----------------------------------------------- | ---------------------------------------- |
| 1.1  | Open browser, clear cookies                     | Cookies cleared                          |
| 1.2  | Navigate to `http://localhost:3000/workspaces`  | Redirected to `/login?next=/workspaces`  |
| 1.3  | Navigate to `http://localhost:3000/admin/users` | Redirected to `/login?next=/admin/users` |
| 1.4  | Navigate to `http://localhost:3000/documents`   | Redirected to `/login?next=/documents`   |

### Test 2: Admin Login and Role Enforcement

| Step | Action                               | Expected Result                                                    |
| ---- | ------------------------------------ | ------------------------------------------------------------------ |
| 2.1  | Go to `/login`                       | Login page displayed                                               |
| 2.2  | Login with admin credentials         | Redirected to `/admin/users` (admin home)                          |
| 2.3  | Manually navigate to `/workspaces`   | Redirected to `/admin/users` (admin cannot access employee portal) |
| 2.4  | Navigate to `/admin/users`           | Page loads successfully                                            |
| 2.5  | Navigate to `/login` while logged in | Redirected to `/admin/users`                                       |

### Test 3: Employee Login and Role Enforcement

| Step | Action                                         | Expected Result                                                    |
| ---- | ---------------------------------------------- | ------------------------------------------------------------------ |
| 3.1  | Logout (clear cookies or visit `/auth/logout`) | Logged out                                                         |
| 3.2  | Go to `/login`                                 | Login page displayed                                               |
| 3.3  | Login with employee credentials                | Redirected to `/workspaces` (employee home)                        |
| 3.4  | Manually navigate to `/admin/users`            | Redirected to `/workspaces` (employee cannot access admin console) |
| 3.5  | Navigate to `/workspaces`                      | Page loads successfully                                            |
| 3.6  | Navigate to `/login` while logged in           | Redirected to `/workspaces`                                        |

### Test 4: Login with Next Parameter

| Step | Action                                             | Expected Result                                                   |
| ---- | -------------------------------------------------- | ----------------------------------------------------------------- |
| 4.1  | Logout                                             | Logged out                                                        |
| 4.2  | Navigate to `/workspaces/some-id` (not logged in)  | Redirected to `/login?next=/workspaces/some-id`                   |
| 4.3  | Login with employee credentials                    | Redirected to `/workspaces/some-id`                               |
| 4.4  | Logout, navigate to `/admin/users` (not logged in) | Redirected to `/login?next=/admin/users`                          |
| 4.5  | Login with employee credentials                    | Redirected to `/workspaces` (ignores next param for wrong portal) |
| 4.6  | Logout and login with admin credentials            | Redirected to `/admin/users`                                      |

### Test 5: Invalid/Expired Cookie

| Step | Action                                                                            | Expected Result                                |
| ---- | --------------------------------------------------------------------------------- | ---------------------------------------------- |
| 5.1  | Login as employee                                                                 | Logged in                                      |
| 5.2  | Manually corrupt the `rag_access_token` cookie (DevTools > Application > Cookies) | Cookie modified                                |
| 5.3  | Refresh page                                                                      | Redirected to `/login`, corrupt cookie cleared |

## Quick Verification Commands

```bash
# Check backend is responding
curl -s http://localhost:8000/health | jq .

# Check auth/me requires authentication
curl -s http://localhost:3000/auth/me
# Expected: 401 Unauthorized

# Check frontend build
cd apps/frontend && npx next build
# Expected: Exit code 0, no errors
```

## DOD Checklist

- [ ] Admin navigating to /workspaces → redirected to /admin/users
- [ ] Employee navigating to /admin → redirected to /workspaces
- [ ] Login page with auth → redirects based on role
- [ ] Invalid cookie → redirects to login
- [ ] No infinite redirect loops
