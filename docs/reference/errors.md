# Errores y RFC7807
Fuente de verdad: `apps/backend/app/crosscutting/error_responses.py` y `apps/backend/app/api/exception_handlers.py`.

## Forma del error (Problem Details)
El backend responde errores con `application/problem+json` y el modelo `ErrorDetail` definido en `apps/backend/app/crosscutting/error_responses.py`.

Campos del payload (`ErrorDetail`):
- `type`
- `title`
- `status`
- `detail`
- `code`
- `instance`
- `errors`

Ejemplo de shape (valores ilustrativos, estructura real):
```json
{
  "type": "about:blank/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Recurso no encontrado",
  "code": "NOT_FOUND",
  "instance": "/v1/workspaces/123",
  "errors": [{"request_id": "..."}]
}
```

## Catálogo de códigos HTTP
Catálogo `ErrorCode` en `apps/backend/app/crosscutting/error_responses.py`:
- `VALIDATION_ERROR`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `NOT_FOUND`
- `CONFLICT`
- `UNSUPPORTED_MEDIA`
- `RATE_LIMITED`
- `PAYLOAD_TOO_LARGE`
- `INTERNAL_ERROR`
- `SERVICE_UNAVAILABLE`
- `LLM_ERROR`
- `EMBEDDING_ERROR`
- `DATABASE_ERROR`

## Mapeos de errores internos → HTTP
- Excepciones internas (`RAGError`, `DatabaseError`, `EmbeddingError`, `LLMError`) se traducen en `apps/backend/app/api/exception_handlers.py`.
- Errores de casos de uso (`DocumentErrorCode`, `WorkspaceErrorCode`) se mapean en `apps/backend/app/interfaces/api/http/error_mapping.py`.

## OpenAPI
Las respuestas RFC7807 se registran en OpenAPI vía `OPENAPI_ERROR_RESPONSES` en `apps/backend/app/crosscutting/error_responses.py` y se aplican en el router raíz (`apps/backend/app/interfaces/api/http/router.py`).
