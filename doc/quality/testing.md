# Estrategia de Testing

## Overview

| Capa | Framework | Cobertura objetivo |
|------|-----------|-------------------|
| Backend | pytest | ≥80% |
| Frontend | Jest + Testing Library | ≥70% |
| E2E | (Planned) Playwright | Flujos críticos |
| Load | k6 | Benchmarks |

## Backend (pytest)

### Ejecutar tests

```bash
cd backend

# Todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Solo unit tests
pytest tests/unit/

# Solo integration tests
pytest tests/integration/

# Test específico
pytest tests/unit/test_answer_query.py -v
```

### Estructura

```
backend/tests/
├── unit/                    # Tests sin I/O externo
│   ├── test_answer_query_use_case.py
│   ├── test_context_builder.py
│   └── test_entities.py
├── integration/             # Tests con DB/APIs
│   └── test_postgres_repo.py
└── conftest.py              # Fixtures compartidos
```

### Fixtures principales

```python
# conftest.py

@pytest.fixture
def mock_embedding_service():
    """Mock de EmbeddingService para unit tests."""
    service = Mock(spec=EmbeddingService)
    service.embed.return_value = [0.1] * 768
    return service

@pytest.fixture
def mock_chunk_repository():
    """Mock de ChunkRepository para unit tests."""
    repo = Mock(spec=ChunkRepository)
    repo.search.return_value = [
        ChunkMatch(chunk_id=uuid4(), document_id=uuid4(), content="test", similarity=0.9)
    ]
    return repo
```

### Patrones de test

#### Unit test de use case

```python
def test_answer_query_returns_answer_with_sources(
    mock_chunk_repository,
    mock_embedding_service,
    mock_llm_service,
):
    use_case = AnswerQueryUseCase(
        chunk_repo=mock_chunk_repository,
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service,
    )
    
    result = use_case.execute(AnswerQueryInput(query="test query"))
    
    assert result.answer is not None
    assert len(result.chunks) > 0
```

#### Integration test con DB

```python
@pytest.mark.integration
def test_postgres_repo_saves_and_retrieves(db_connection):
    repo = PostgresDocumentRepository(db_connection)
    doc = Document(id=uuid4(), title="Test")
    
    repo.save(doc)
    retrieved = repo.get_by_id(doc.id)
    
    assert retrieved.title == "Test"
```

### Configuración (pytest.ini)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
markers =
    integration: marks tests as integration (require DB)
    slow: marks tests as slow running
addopts = -v --tb=short
```

## Frontend (Jest)

### Ejecutar tests

```bash
cd frontend

# Todos los tests
pnpm test

# Watch mode
pnpm test -- --watch

# Con cobertura
pnpm test -- --coverage

# Test específico
pnpm test -- useRagAsk
```

### Estructura

```
frontend/__tests__/
├── components/
│   └── ChatInput.test.tsx
├── hooks/
│   └── useRagAsk.test.ts
└── pages/
    └── Home.test.tsx
```

### Configuración (jest.config.js)

```javascript
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  collectCoverageFrom: [
    'app/**/*.{ts,tsx}',
    '!app/**/*.d.ts',
  ],
};
```

### Patrones de test

#### Test de hook con mock

```typescript
import { renderHook, act } from '@testing-library/react';
import { useRagAsk } from '@/app/hooks/useRagAsk';

jest.mock('@/app/api/client', () => ({
  ask: jest.fn().mockResolvedValue({ answer: 'test', sources: [] }),
}));

test('useRagAsk returns answer on success', async () => {
  const { result } = renderHook(() => useRagAsk());
  
  await act(async () => {
    await result.current.ask('test query');
  });
  
  expect(result.current.answer).toBe('test');
});
```

## Load Testing (k6)

### Ejecutar

```bash
cd tests/load
k6 run scenarios/ask_endpoint.js
```

### Script ejemplo

```javascript
// tests/load/scenarios/ask_endpoint.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500'],
  },
};

export default function () {
  const res = http.post(
    'http://localhost:8000/v1/ask',
    JSON.stringify({ query: 'test query', top_k: 3 }),
    {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'dev-key',
      },
    }
  );
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'has answer': (r) => JSON.parse(r.body).answer !== undefined,
  });
  
  sleep(1);
}
```

## CI/CD

Tests corren automáticamente en GitHub Actions:

```yaml
# .github/workflows/test.yml
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests --cov=backend/app

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - run: pnpm install
      - run: pnpm --filter frontend test
```

## Cobertura actual

Ver reporte HTML generado:
- Backend: `backend/htmlcov/index.html`
- Frontend: `frontend/coverage/lcov-report/index.html`
