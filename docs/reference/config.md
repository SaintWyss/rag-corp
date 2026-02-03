# Configuration Reference

| Name           | Default | Source | Impact            | Example                             |
| -------------- | ------- | ------ | ----------------- | ----------------------------------- |
| `DATABASE_URL` | -       | Env    | DB Connection     | `postgres://user:pass@host:5432/db` |
| `LOG_LEVEL`    | INFO    | Env    | Logging verbosity | `DEBUG`                             |

## Flags & Limits

- Rate Limits: Configured in `app/crosscutting/limiter.py`
