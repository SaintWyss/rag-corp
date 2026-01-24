# ADR-003: Google Gemini como proveedor LLM

## Estado

**Aceptado** (2024-12)

## Contexto

El sistema RAG necesita:
1. **Servicio de embeddings**: Convertir texto a vectores 768D
2. **Servicio de generación**: Responder preguntas con contexto

Opciones evaluadas:
- OpenAI (GPT-4, text-embedding-3)
- Anthropic (Claude)
- Google (Gemini)
- Modelos locales (Ollama + Llama)

## Decisión

Usamos **Google Gemini** con dos modelos:

| Función | Modelo | Dimensiones |
|---------|--------|-------------|
| Embeddings | `text-embedding-004` | 768 |
| Generación | `gemini-2.0-flash-001` | N/A |

### Implementación

```python
# apps/backend/app/infrastructure/services/google_embedding.py
class GoogleEmbeddingService:
    model = "text-embedding-004"
    
# apps/backend/app/infrastructure/services/google_llm.py  
class GoogleLLMService:
    model = "gemini-2.0-flash-001"
```

### Configuración

```bash
# Variable de entorno requerida
GOOGLE_API_KEY=your-api-key
```

## Consecuencias

### Positivas

- **Costo**: Tier gratuito generoso para desarrollo
- **Latencia**: ~200-500ms para embeddings, ~1-3s para generación
- **Calidad**: text-embedding-004 comparable a OpenAI ada-002
- **SDK**: `google-generativeai` bien documentado

### Negativas

- **Vendor lock-in**: Embeddings de 768D específicos de Google
- **Rate limits**: 60 RPM en tier gratuito
- **Disponibilidad**: Dependencia de servicio externo

## Mitigaciones

1. **Retry con backoff**: `infrastructure/services/retry.py` maneja errores transitorios
2. **Abstracción**: Protocols en Domain permiten cambiar proveedor
3. **Fallback**: Configurable vía `LLM_FALLBACK_ENABLED` para modelo local (Ollama)

### Fallback a modelo local

Para habilitar fallback a Ollama cuando Google API no está disponible:

```bash
# .env
LLM_FALLBACK_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Comportamiento:
- Si Google API falla 3 veces consecutivas → switch a Ollama
- Requiere Ollama corriendo localmente
- Embeddings permanecen en Google (re-embedding sería costoso)

## Migración futura

Si cambiamos de proveedor:
1. Implementar nueva clase en `infrastructure/services/`
2. Re-generar embeddings (dimensiones pueden diferir)
3. Actualizar índice pgvector

## Referencias

- [Google AI Studio](https://aistudio.google.com/)
- [text-embedding-004 docs](https://ai.google.dev/gemini-api/docs/models/gemini#text-embedding)
- [apps/backend/app/infrastructure/services/](../../../apps/backend/app/infrastructure/services/)
