# Access Control Matrix

| Actor/Role | Action | Resource  | Condition |
| ---------- | ------ | --------- | --------- |
| Admin      | \*     | \*        | -         |
| User       | Read   | Workspace | Owner     |

Links to policies:

- `apps/backend/app/crosscutting/auth`
