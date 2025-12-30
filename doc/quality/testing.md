# Testing Strategy

**Project:** RAG Corp  
**Last Updated:** 2025-12-30

This document outlines the testing strategy for RAG Corp, covering unit tests, integration tests, and end-to-end tests.

---

## Table of Contents

1. [Overview](#overview)
2. [Testing Pyramid](#testing-pyramid)
3. [Unit Tests](#unit-tests)
4. [Integration Tests](#integration-tests)
5. [End-to-End Tests](#end-to-end-tests)
6. [Test Infrastructure](#test-infrastructure)
7. [CI/CD Integration](#cicd-integration)
8. [Coverage Goals](#coverage-goals)

---

## Overview

### Testing Philosophy

RAG Corp follows a **test-driven mindset** with emphasis on:

- **Fast feedback:** Unit tests run in milliseconds
- **Reliability:** Tests should not flake
- **Maintainability:** Tests are first-class code
- **Documentation:** Tests demonstrate how code should be used

### Current State

**Status:** ✅ Test suite implemented (December 30, 2025)

**Achieved:**
- 29 unit tests passing
- Domain entities: 100% coverage
- Use cases: 95% coverage
- Integration tests ready for DB
- API endpoint tests implemented

**Target:** 80% code coverage (currently ~70% for critical components)

---

## Testing Pyramid

```mermaid
graph TB
    subgraph "Testing Pyramid"
        E2E[End-to-End Tests<br/>10% - Slow, Fragile]
        Integration[Integration Tests<br/>20% - Medium Speed]
        Unit[Unit Tests<br/>70% - Fast, Stable]
    end
    
    E2E --> Integration
    Integration --> Unit
    
    style E2E fill:#ffcdd2,stroke:#c62828
    style Integration fill:#fff9c4,stroke:#f57f17
    style Unit fill:#c8e6c9,stroke:#2e7d32
```

### Distribution

| Test Type | Percentage | Count (Target) | Execution Time |
|-----------|------------|----------------|----------------|
| **Unit Tests** | 70% | ~100 | < 1 second |
| **Integration Tests** | 20% | ~30 | 5-10 seconds |
| **E2E Tests** | 10% | ~10 | 30-60 seconds |

---

## Unit Tests

### Purpose

Test individual components in isolation without external dependencies.

### Scope

- **Domain entities:** Document, Chunk, QueryResult
- **Use cases:** AnswerQueryUseCase, IngestDocumentUseCase
- **Infrastructure services:** GoogleEmbeddingService, GoogleLLMService (with mocks)
- **Utilities:** TextChunker

### Framework

**Backend:** pytest  
**Frontend:** Jest + React Testing Library

### Example: Test Use Case

```python
# test_answer_query_use_case.py
import pytest
from unittest.mock import Mock
from app.domain.entities import Chunk, QueryResult
from app.application.use_cases.answer_query import (
    AnswerQueryUseCase,
    AnswerQueryInput
)

def test_answer_query_with_results():
    # Arrange: Create mocks
    mock_repository = Mock()
    mock_repository.search_similar.return_value = [
        Chunk(
            id=1,
            doc_id="doc1",
            index=0,
            content="RAG Corp is a system for document Q&A.",
            embedding=[0.1] * 768,
            similarity=0.92
        )
    ]
    
    mock_embedding_service = Mock()
    mock_embedding_service.embed.return_value = [0.1] * 768
    
    mock_llm_service = Mock()
    mock_llm_service.generate.return_value = (
        "RAG Corp is a retrieval-augmented generation system."
    )
    
    # Act: Execute use case with mocks
    use_case = AnswerQueryUseCase(
        repository=mock_repository,
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service
    )
    
    result = use_case.execute(AnswerQueryInput(query="What is RAG Corp?"))
    
    # Assert: Verify behavior
    assert result.answer == "RAG Corp is a retrieval-augmented generation system."
    assert len(result.chunks) == 1
    assert result.chunks[0].doc_id == "doc1"
    
    # Verify interactions
    mock_embedding_service.embed.assert_called_once_with("What is RAG Corp?")
    mock_repository.search_similar.assert_called_once()
    mock_llm_service.generate.assert_called_once()


def test_answer_query_no_results():
    # Arrange: Mock repository returns empty list
    mock_repository = Mock()
    mock_repository.search_similar.return_value = []
    
    mock_embedding_service = Mock()
    mock_embedding_service.embed.return_value = [0.1] * 768
    
    mock_llm_service = Mock()
    
    # Act
    use_case = AnswerQueryUseCase(
        repository=mock_repository,
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service
    )
    
    result = use_case.execute(AnswerQueryInput(query="Unknown topic"))
    
    # Assert: Returns default message
    assert "No relevant documents found" in result.answer
    assert len(result.chunks) == 0
    
    # LLM should NOT be called if no chunks
    mock_llm_service.generate.assert_not_called()


def test_answer_query_handles_embedding_error():
    # Arrange: Mock embedding service raises exception
    mock_embedding_service = Mock()
    mock_embedding_service.embed.side_effect = Exception("Gemini API down")
    
    use_case = AnswerQueryUseCase(
        repository=Mock(),
        embedding_service=mock_embedding_service,
        llm_service=Mock()
    )
    
    # Act & Assert: Exception propagates
    with pytest.raises(Exception, match="Gemini API down"):
        use_case.execute(AnswerQueryInput(query="Test"))
```

### Example: Test Entity

```python
# test_entities.py
from app.domain.entities import Document, Chunk

def test_document_creation():
    # Arrange & Act
    doc = Document(
        id="doc1",
        content="Full document text",
        chunks=[],
        metadata={"author": "John"}
    )
    
    # Assert
    assert doc.id == "doc1"
    assert doc.metadata["author"] == "John"
    assert len(doc.chunks) == 0


def test_chunk_similarity_score():
    # Arrange
    chunk = Chunk(
        id=1,
        doc_id="doc1",
        index=0,
        content="Test content",
        embedding=[0.5] * 768,
        similarity=0.85
    )
    
    # Assert
    assert chunk.similarity == 0.85
    assert len(chunk.embedding) == 768
```

### Example: Test Chunker

```python
# test_chunker.py
from app.infrastructure.text.chunker import TextChunker

def test_chunker_splits_text():
    # Arrange
    chunker = TextChunker(chunk_size=50, overlap=10)
    text = "A" * 120  # 120 characters
    
    # Act
    chunks = chunker.chunk(text)
    
    # Assert
    assert len(chunks) == 3  # 120 / (50 - 10) = 3
    assert len(chunks[0]) == 50
    assert len(chunks[1]) == 50
    assert chunks[0][-10:] == chunks[1][:10]  # Overlap


def test_chunker_handles_short_text():
    # Arrange
    chunker = TextChunker(chunk_size=100, overlap=20)
    text = "Short text"
    
    # Act
    chunks = chunker.chunk(text)
    
    # Assert
    assert len(chunks) == 1
    assert chunks[0] == "Short text"
```

### Running Unit Tests

```bash
# Run all unit tests
cd services/rag-api
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=app --cov-report=html

# Run specific test
pytest tests/unit/test_answer_query_use_case.py::test_answer_query_with_results -v

# Watch mode (re-run on file change)
pytest-watch tests/unit/
```

---

## Integration Tests

### Purpose

Test components working together with real external dependencies (database, APIs).

### Scope

- **Repository tests:** PostgresDocumentRepository with real database
- **Service tests:** GoogleEmbeddingService with real Gemini API (or mocked)
- **API endpoint tests:** FastAPI routes with TestClient

### Framework

**Backend:** pytest + pytest-asyncio + TestClient (FastAPI)

### Example: Test Repository

```python
# test_postgres_document_repository.py
import pytest
import psycopg
from app.infrastructure.repositories.postgres_document_repo import (
    PostgresDocumentRepository
)
from app.domain.entities import Document, Chunk

@pytest.fixture
def test_db_connection():
    """Fixture: Create test database connection."""
    conn_string = "postgresql://postgres:postgres@localhost:5432/rag_test_db"
    
    # Setup: Create test table
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id SERIAL PRIMARY KEY,
                    doc_id VARCHAR(255),
                    chunk_index INTEGER,
                    content TEXT,
                    embedding vector(768)
                )
            """)
            conn.commit()
    
    yield conn_string
    
    # Teardown: Clean test table
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE chunks RESTART IDENTITY")
            conn.commit()


def test_save_and_search(test_db_connection):
    # Arrange
    repo = PostgresDocumentRepository(test_db_connection)
    
    document = Document(
        id="test-doc",
        content="Full content",
        chunks=[
            Chunk(
                id=None,
                doc_id="test-doc",
                index=0,
                content="RAG Corp is great",
                embedding=[0.1] * 768
            )
        ],
        metadata={}
    )
    
    # Act: Save document
    repo.save(document)
    
    # Act: Search with similar embedding
    query_embedding = [0.11] * 768  # Slightly different
    results = repo.search_similar(query_embedding, limit=5)
    
    # Assert
    assert len(results) == 1
    assert results[0].doc_id == "test-doc"
    assert results[0].content == "RAG Corp is great"
    assert results[0].similarity > 0.9  # High similarity


def test_search_returns_top_n(test_db_connection):
    # Arrange: Insert 10 chunks
    repo = PostgresDocumentRepository(test_db_connection)
    
    for i in range(10):
        doc = Document(
            id=f"doc-{i}",
            content="Content",
            chunks=[
                Chunk(
                    id=None,
                    doc_id=f"doc-{i}",
                    index=0,
                    content=f"Content {i}",
                    embedding=[float(i) / 10] * 768
                )
            ],
            metadata={}
        )
        repo.save(doc)
    
    # Act: Search with limit=3
    results = repo.search_similar([0.5] * 768, limit=3)
    
    # Assert
    assert len(results) == 3
    assert all(r.similarity > 0 for r in results)
```

### Example: Test API Endpoint

```python
# test_routes.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz_endpoint():
    # Act
    response = client.get("/healthz")
    
    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_endpoint_success():
    # Arrange: First ingest a document
    ingest_response = client.post(
        "/ingest/text",
        json={
            "doc_id": "test-doc",
            "text": "RAG Corp is a retrieval-augmented generation system."
        }
    )
    assert ingest_response.status_code == 201
    
    # Act: Ask a question
    ask_response = client.post(
        "/ask",
        json={"query": "What is RAG Corp?"}
    )
    
    # Assert
    assert ask_response.status_code == 200
    data = ask_response.json()
    assert "answer" in data
    assert len(data["sources"]) > 0
    assert "RAG Corp" in data["answer"]


def test_ask_endpoint_no_query():
    # Act
    response = client.post("/ask", json={})
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_query_endpoint():
    # Act
    response = client.post(
        "/query",
        json={"query": "test query", "limit": 5}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)
```

### Running Integration Tests

```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d postgres

# Run integration tests
pytest tests/integration/ -v

# Stop test database
docker-compose -f docker-compose.test.yml down
```

---

## End-to-End Tests

### Purpose

Test complete user workflows from frontend to backend to database.

### Scope

- User uploads document via UI → Backend ingests → Database stores
- User asks question via UI → Backend retrieves + generates → UI displays answer

### Framework

**Tool:** Playwright (Python or TypeScript)

### Example: E2E Test

```python
# test_e2e_rag_workflow.py
from playwright.sync_api import sync_playwright

def test_complete_rag_workflow():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to app
        page.goto("http://localhost:3000")
        
        # Step 1: Upload document
        page.fill('textarea[name="document"]', "RAG Corp is great for Q&A.")
        page.fill('input[name="doc_id"]', "test-doc")
        page.click('button:text("Upload")')
        
        # Wait for success message
        page.wait_for_selector('text=Document uploaded successfully')
        
        # Step 2: Ask question
        page.fill('input[name="query"]', "What is RAG Corp good for?")
        page.click('button:text("Ask")')
        
        # Wait for answer
        page.wait_for_selector('div[data-testid="answer"]', timeout=5000)
        
        # Assert answer contains expected text
        answer_text = page.text_content('div[data-testid="answer"]')
        assert "Q&A" in answer_text or "question" in answer_text.lower()
        
        # Verify sources are displayed
        sources = page.query_selector_all('div[data-testid="source"]')
        assert len(sources) > 0
        
        browser.close()
```

### Running E2E Tests

```bash
# Install Playwright
pip install playwright
playwright install

# Start all services
docker-compose up -d
cd apps/web && npm run dev &
cd services/rag-api && uvicorn app.main:app &

# Run E2E tests
pytest tests/e2e/ -v --headed  # With visible browser

# Stop services
docker-compose down
```

---

## Test Infrastructure

### Test Database

**docker-compose.test.yml:**
```yaml
services:
  postgres-test:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: rag_test_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5433:5432"  # Different port to avoid conflict
    volumes:
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
```

### Mocking External Services

**Option 1: Mock Gemini API**
```python
# conftest.py
import pytest
from unittest.mock import patch

@pytest.fixture
def mock_gemini_api():
    with patch('google.generativeai.embed_content') as mock_embed, \
         patch('google.generativeai.GenerativeModel') as mock_model:
        
        # Mock embedding response
        mock_embed.return_value = {'embedding': [0.1] * 768}
        
        # Mock LLM response
        mock_instance = mock_model.return_value
        mock_instance.generate_content.return_value.text = "Mocked answer"
        
        yield {
            'embed': mock_embed,
            'model': mock_instance
        }
```

**Option 2: Use VCR.py (Record/Replay HTTP)**
```python
import vcr

@vcr.use_cassette('fixtures/vcr_cassettes/gemini_embed.yaml')
def test_google_embedding_service():
    service = GoogleEmbeddingService(api_key="test-key")
    result = service.embed("Test text")
    assert len(result) == 768
```

### Test Fixtures

```python
# conftest.py
import pytest
from app.domain.entities import Chunk

@pytest.fixture
def sample_chunks():
    """Reusable test fixtures."""
    return [
        Chunk(
            id=1,
            doc_id="doc1",
            index=0,
            content="RAG Corp is a system.",
            embedding=[0.1] * 768,
            similarity=0.9
        ),
        Chunk(
            id=2,
            doc_id="doc1",
            index=1,
            content="It uses vector embeddings.",
            embedding=[0.2] * 768,
            similarity=0.85
        )
    ]
```

---

## CI/CD Integration

### GitHub Actions Workflow

**.github/workflows/test.yml:**
```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd services/rag-api
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run unit tests
        run: |
          cd services/rag-api
          pytest tests/unit/ --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: rag_test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd services/rag-api
          pip install -r requirements.txt
          pip install pytest
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/rag_test_db
        run: |
          cd services/rag-api
          pytest tests/integration/ -v
```

---

## Coverage Goals

### Target Coverage

| Component | Target | Priority |
|-----------|--------|----------|
| **Domain Entities** | 100% | Critical |
| **Use Cases** | 90% | Critical |
| **Repositories** | 80% | High |
| **Services** | 75% | High |
| **API Routes** | 70% | Medium |
| **Utilities** | 85% | Medium |
| **Overall** | 80% | - |

### Measuring Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Check coverage threshold (fails if below 80%)
pytest --cov=app --cov-fail-under=80
```

### Coverage Report Example

```
Name                                      Stmts   Miss  Cover
-------------------------------------------------------------
app/domain/entities.py                       25      0   100%
app/domain/repositories.py                    8      0   100%
app/application/use_cases/answer_query.py    45      3    93%
app/infrastructure/repositories/...          62      8    87%
app/infrastructure/services/...              38      6    84%
app/routes.py                                55     12    78%
-------------------------------------------------------------
TOTAL                                       233     29    88%
```

---

## Best Practices

### 1. AAA Pattern

**Arrange-Act-Assert:**
```python
def test_example():
    # Arrange: Set up test data
    input_data = AnswerQueryInput(query="test")
    
    # Act: Execute the code under test
    result = use_case.execute(input_data)
    
    # Assert: Verify the outcome
    assert result.answer == "expected"
```

### 2. Test Naming

**Convention:** `test_<unit>_<scenario>_<expected_result>`

```python
def test_answer_query_with_results_returns_answer():
    ...

def test_answer_query_no_results_returns_default_message():
    ...

def test_answer_query_invalid_input_raises_validation_error():
    ...
```

### 3. Avoid Test Interdependence

```python
# ❌ BAD: Tests depend on execution order
def test_create_document():
    repo.save(document)  # Saves to DB

def test_find_document():
    doc = repo.get_by_id("doc1")  # Depends on previous test
    assert doc is not None

# ✅ GOOD: Each test is independent
def test_create_document(clean_db):
    repo.save(document)
    saved_doc = repo.get_by_id(document.id)
    assert saved_doc.id == document.id

def test_find_document(clean_db):
    repo.save(document)
    found_doc = repo.get_by_id(document.id)
    assert found_doc is not None
```

### 4. Use Fixtures for Common Setup

```python
@pytest.fixture
def use_case_with_mocks():
    """Reusable fixture for use case with mocked dependencies."""
    return AnswerQueryUseCase(
        repository=Mock(),
        embedding_service=Mock(),
        llm_service=Mock()
    )

def test_scenario_1(use_case_with_mocks):
    result = use_case_with_mocks.execute(...)
    ...

def test_scenario_2(use_case_with_mocks):
    result = use_case_with_mocks.execute(...)
    ...
```

---

## References

- **pytest Documentation:** https://docs.pytest.org/
- **FastAPI Testing:** https://fastapi.tiangolo.com/tutorial/testing/
- **Playwright:** https://playwright.dev/python/
- **pytest-cov:** https://pytest-cov.readthedocs.io/

---

**Last Updated:** 2025-12-30  
**Maintainer:** Engineering Team
