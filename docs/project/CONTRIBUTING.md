# Contributing to RAG Corp

First off, thank you for considering contributing to RAG Corp! 🎉

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- pnpm 9+
- Docker & Docker Compose
- Google API Key (for Gemini)

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/SaintWyss/rag-corp.git
cd rag-corp

# 2. Configure environment
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY

# 3. Install dependencies
pnpm install

# 4. Start services
pnpm stack:core

# 5. Run dev servers
pnpm dev
```

For detailed setup instructions, see [docs/runbook/local-dev.md](../runbook/local-dev.md).

## Development Workflow

### Branch Naming

Use descriptive branch names with prefixes:

- `feat/` - New features (e.g., `feat/semantic-search-v2`)
- `fix/` - Bug fixes (e.g., `fix/embedding-cache-ttl`)
- `docs/` - Documentation updates (e.g., `docs/api-examples`)
- `refactor/` - Code refactoring (e.g., `refactor/chunker-interface`)
- `test/` - Test additions/improvements (e.g., `test/e2e-rag-flow`)
- `chore/` - Maintenance tasks (e.g., `chore/update-deps`)

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Examples:**

```
feat(backend): add semantic chunking with section awareness
fix(frontend): handle empty query submission gracefully
docs(api): add rate limiting examples to http-api.md
test(e2e): add document upload flow tests
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`

### Making Changes

1. **Create a branch** from `main`:

   ```bash
   git checkout -b feat/your-feature
   ```

2. **Make your changes** following the style guidelines

3. **Run tests** to ensure nothing is broken:

   ```bash
   # Backend
   cd apps/backend && pytest

   # Frontend
   cd apps/frontend && pnpm test

   # E2E (requires services running)
   pnpm e2e
   ```

4. **Commit your changes** with a descriptive message

5. **Push and create a PR**

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally (`pytest`, `pnpm test`)
- [ ] Linting passes (`ruff check`, `pnpm lint`)
- [ ] Documentation updated (if applicable)
- [ ] CHANGELOG.md updated (for user-facing changes)
- [ ] No console.log/print statements left in code

### PR Description

Use this template:

```markdown
## Summary

Brief description of what this PR does.

## Changes

- Change 1
- Change 2

## Testing

How was this tested?

## Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG updated
```

### Review Process

1. Create PR against `main`
2. CI checks must pass
3. At least one maintainer approval required
4. Squash and merge preferred

## Style Guidelines

### Python (Backend)

- **Formatter:** Ruff
- **Linter:** Ruff
- **Type Hints:** Required for all public functions
- **Docstrings:** Google style

```python
def process_document(content: str, chunk_size: int = 900) -> list[Chunk]:
    """
    Process a document into semantic chunks.

    Args:
        content: Raw document text
        chunk_size: Maximum chunk size in characters

    Returns:
        List of Chunk objects with embeddings

    Raises:
        ValueError: If content is empty
    """
    ...
```

### TypeScript (Frontend)

- **Formatter:** Prettier (via ESLint)
- **Linter:** ESLint with Next.js config
- **Type Safety:** Strict mode enabled

```typescript
type QueryFormProps = {
  query: string;
  onSubmit: (query: string) => Promise<void>;
  loading: boolean;
};

export function QueryForm({ query, onSubmit, loading }: QueryFormProps) {
  // ...
}
```

### SQL (Migrations)

- Use Alembic for all schema changes
- Include both `upgrade()` and `downgrade()`
- Test migrations in both directions

## Testing

### Backend Tests

```bash
cd apps/backend

# Unit tests (fast, no external deps)
pytest -m unit

# Integration tests (requires DB + API key)
RUN_INTEGRATION=1 GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY_HERE pytest -m integration

# All tests with coverage
pytest --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd apps/frontend

# Run tests
pnpm test

# Watch mode
pnpm test:watch

# Coverage (must meet 70% threshold)
pnpm test:coverage
```

### E2E Tests

```bash
# Start services first
pnpm stack:core

# Run E2E tests
pnpm e2e

# Interactive mode
pnpm e2e:ui
```

### Load Tests

```bash
# Run k6 load tests
cd tests/load
k6 run api.k6.js --env BASE_URL=http://localhost:8000
```

## Documentation

### When to Update Docs

- New features → Update relevant docs
- API changes → Update `docs/reference/api/http-api.md`
- Architecture changes → Update `docs/architecture/overview.md`
- New environment variables → Update `docs/runbook/local-dev.md`

### Doc Locations

| Topic             | Location                                 |
| ----------------- | ---------------------------------------- |
| Architecture      | `docs/architecture/overview.md`          |
| API Reference     | `docs/reference/api/http-api.md`         |
| Database Schema   | `docs/reference/data/postgres-schema.md` |
| Local Development | `docs/runbook/local-dev.md`              |
| Deployment        | `docs/runbook/deployment.md`             |
| Troubleshooting   | `docs/runbook/troubleshooting.md`        |

## Questions?

- Check existing issues and PRs
- Open a discussion in GitHub Discussions
- For security issues, see [SECURITY.md](SECURITY.md)

---

Thank you for contributing! 🚀
