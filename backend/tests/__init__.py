"""
RAG Corp API Test Suite

Test organization:
- unit/: Fast tests without external dependencies (domain, application layer)
- integration/: Tests requiring DB or external services (infrastructure)
- api/: End-to-end API tests

Run tests:
    pytest                           # All tests
    pytest -m unit                   # Only unit tests
    pytest -m integration            # Only integration tests
    pytest tests/unit/               # Specific directory
    pytest -k test_answer_query      # Specific test name pattern
"""
