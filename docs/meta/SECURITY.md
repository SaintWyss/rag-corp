# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of RAG Corp seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **security@ragcorp.example.com**

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

### What to Include

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### What to Expect

- **Acknowledgment**: We will acknowledge your email within 48 hours
- **Communication**: We will keep you informed of the progress towards a fix
- **Disclosure**: We will coordinate the public disclosure date with you
- **Credit**: We will credit you in our release notes (unless you prefer to remain anonymous)

## Security Best Practices

### API Authentication

RAG Corp uses API key authentication with scoped permissions:

```
X-API-Key: <your-api-key>
```

**Scopes:**
- `ingest` - Document ingestion operations
- `ask` - Query and RAG operations  
- `metrics` - Prometheus metrics access

### Rate Limiting

The API implements token bucket rate limiting:
- Default: 10 requests/second per IP
- Configurable via `RATE_LIMIT_RPS` environment variable

### Security Headers

All responses include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`
- `X-XSS-Protection: 1; mode=block`

### Input Validation

- All inputs are validated using Pydantic with strict type checking
- Query strings are limited to 2000 characters
- Document content is limited to 1MB
- File uploads are restricted to allowed MIME types

### CORS Configuration

CORS is configured with explicit origins:
```
ALLOWED_ORIGINS=https://app.ragcorp.example.com,https://admin.ragcorp.example.com
```

### Database Security

- Connection pooling with limited connections
- Parameterized queries (no raw SQL interpolation)
- Credentials stored in environment variables (never in code)

## Known Security Considerations

### Prompt Injection

The RAG system includes protections against prompt injection:
- Context is clearly delimited in prompts
- System instructions cannot be overridden by document content
- User input is sanitized before embedding

### Data Privacy

- Documents are stored with embeddings in PostgreSQL
- No data is sent to external services except Google Gemini API
- Logs are structured JSON and do not contain sensitive content

## Security Updates

Security updates will be released as patch versions (0.1.x) and announced via:
- GitHub Security Advisories
- Release notes

## Compliance

This project follows security best practices aligned with:
- OWASP Top 10
- CWE/SANS Top 25

---

*Last updated: 2026-01-13*
