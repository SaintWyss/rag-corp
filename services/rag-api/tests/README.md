# RAG Corp API - Test Suite

## Overview

Suite completa de tests para RAG Corp API, organizada en tests unitarios e integración siguiendo los principios de Clean Architecture.

## Estructura

```
tests/
├── conftest.py                          # Fixtures compartidas y configuración
├── unit/                                # Tests unitarios (rápidos, sin deps externas)
│   ├── test_domain_entities.py          # Tests de entidades del dominio
│   └── test_answer_query_use_case.py    # Tests del caso de uso principal
└── integration/                         # Tests de integración (requieren DB/APIs)
    ├── test_postgres_document_repo.py   # Tests del repositorio PostgreSQL
    └── test_api_endpoints.py            # Tests end-to-end de la API
```

## Ejecutar Tests

### Todos los tests (unit + integration si RUN_INTEGRATION=1)
```bash
pytest
```

### Solo tests unitarios (rápidos)
```bash
pytest -m unit
```

### Solo tests de integración
```bash
RUN_INTEGRATION=1 pytest -m integration
```

### Con reporte de cobertura
```bash
pytest --cov=app --cov-report=html
```

### Tests específicos
```bash
pytest tests/unit/test_domain_entities.py
pytest -k test_answer_query
```

## Requisitos

### Tests Unitarios
- No requieren dependencias externas
- Usan mocks para todas las dependencias
- Ejecución < 1 segundo

### Tests de Integración
- Requieren PostgreSQL en ejecución:
  ```bash
  docker compose up -d db
  ```
- Requieren `DATABASE_URL` configurado (default: localhost:5432)
- Requieren `GOOGLE_API_KEY`
- Se ejecutan solo si `RUN_INTEGRATION=1`

## Cobertura

Objetivo de cobertura: **>=70%** para componentes críticos (configurado en `pytest.ini`)

### Cobertura Actual

TODO: generar reporte y actualizar métricas reales.

## Fixtures Principales

### Entidades de Dominio
- `sample_document`: Documento de prueba
- `sample_chunk`: Chunk individual
- `sample_chunks`: Lista de chunks (3)
- `sample_query_result`: Resultado RAG completo

### Mocks
- `mock_repository`: Mock de DocumentRepository
- `mock_embedding_service`: Mock de EmbeddingService
- `mock_llm_service`: Mock de LLMService

### Factories
- `DocumentFactory`: Crear documentos personalizados
- `ChunkFactory`: Crear chunks personalizados

## Ejemplo de Uso

```python
import pytest
from app.application.use_cases import AnswerQueryUseCase, AnswerQueryInput

@pytest.mark.unit
def test_my_feature(mock_repository, mock_embedding_service, mock_llm_service):
    # Arrange
    use_case = AnswerQueryUseCase(
        repository=mock_repository,
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service
    )
    
    # Act
    result = use_case.execute(AnswerQueryInput(query="test"))
    
    # Assert
    assert result.answer is not None
```

## Markers

- `@pytest.mark.unit`: Tests unitarios
- `@pytest.mark.integration`: Tests de integración
- `@pytest.mark.slow`: Tests lentos (>1s)
- `@pytest.mark.api`: Tests de API

## Mejores Prácticas

1. **Naming**: `test_<method>_<scenario>_<expected_result>`
2. **AAA Pattern**: Arrange → Act → Assert
3. **Isolation**: Cada test es independiente
4. **Fast Unit Tests**: < 10ms por test unitario
5. **Cleanup**: Tests de integración limpian sus datos
6. **Mock External Services**: Nunca llamar APIs reales en tests unitarios

## Pendientes (TODOs)

- [ ] Tests de chunker (infrastructure/text/)
- [ ] Tests de servicios Google (mocked)
- [ ] Tests de manejo de errores (excepciones)
- [ ] Tests de rendimiento (benchmarks)
- [ ] Tests de concurrencia
- [ ] CI/CD integration (GitHub Actions)

## Troubleshooting

### Tests de integración fallan con "connection refused"
```bash
# Verificar que PostgreSQL esté corriendo
docker compose ps
docker compose up -d db
```

### Import errors
```bash
# Instalar dependencias de testing
pip install -r requirements.txt
```

### Cobertura baja
```bash
# Ver reporte detallado en HTML
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Referencias

- [Pytest Documentation](https://docs.pytest.org/)
- [Clean Architecture Testing Patterns](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Testing FastAPI Applications](https://fastapi.tiangolo.com/tutorial/testing/)
