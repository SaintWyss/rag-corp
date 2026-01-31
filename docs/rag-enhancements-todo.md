# Pendientes de Mejoras RAG (Query Rewriting & Reranking)

Este documento lista las tareas pendientes para llevar las mejoras de RAG (Query Rewriting y Chunk Reranking) a un estado de producción robusto ("Enterprise Grade").

## 1. ⚠️ Tests y Calidad (Prioridad Alta)

El objetivo es asegurar la estabilidad del CI y la robustez ante fallos.

- [ ] **Subir Cobertura de Tests Unitarios**
  - `AnswerQueryWithHistoryUseCase` tiene una cobertura actual baja (~56%).
  - Agregar test para **Fallback de Error**: Simular excepción en `rewriter.rewrite()` y verificar que se usa la query original.
  - Agregar test para **Rewriter Deshabilitado**: Verificar comportamiento cuando `query_rewriter` es `None`.
  - Agregar test para **Validación de Metadata**: Asegurar que `_META_REWRITE_ORIGINAL` y `reason` llegan a la respuesta final.

- [ ] **Tests de Integración (E2E)**
  - Crear un flujo completo que ejercite: `Rewrite -> Retrieve -> Rerank`.
  - Verificar que el `ChunkReranker` efectivamente reordena los resultados en un escenario controlado con base de datos real.

## 2. ⚡ Performance y Latencia

El rewriter y reranker agregan pasos secuenciales que aumentan la latencia. Debemos optimizar.

- [ ] **Modelos Específicos (Lightweight Models)**
  - Permitir configurar modelos más rápidos (ej: `gemini-flash`, `gpt-3.5-turbo`) específicamente para rewrite/rerank, separados del modelo de generación principal.
  - Actualizar `config.py` y `LLMService` para soportar `model_alias` por operación.

- [ ] **Timeouts y Circuit Breakers**
  - Implementar un timeout estricto (ej: 1s) para el Rewriter. Si tarda más, cortar y usar query original.
  - Implementar lógica de Circuit Breaker: si el rewriter falla repetidamente, desactivarlo temporalmente automáticamente.

## 3. 🔍 Observabilidad

Necesitamos ver qué está pasando "bajo el capó" en producción.

- [ ] **Logs Estructurados con Trace ID**
  - Asegurar que los logs de `Query rewrite evaluated` incluyan el `trace_id` de la petición para correlacionar con la respuesta final.

- [ ] **Métricas Prometheus**
  - Definir e instrumentar los siguientes contadores/histogramas:
    - `rag_rewrite_total_counter`: Etiquetas `status={success, fallback, skipped}`.
    - `rag_rewrite_latency_seconds_histogram`: Para medir overhead.
    - `rag_rerank_docs_count_histogram`: Cuántos docs entran vs cuántos salen.

## 4. 🧹 Limpieza de Código (Refactor)

Deuda técnica acumulada durante la implementación rápida.

- [ ] **Unificar `conversations.py`**
  - El archivo `app/application/conversations.py` fue creado como alias temporal para arreglar imports rotos.
  - Mover su lógica oficialmente a `app/application/usecases/chat/chat_utils.py` (o ubicación definitiva).
  - Actualizar todas las referencias en imports y borrar `conversations.py`.

- [ ] **Consistencia de DTOs**
  - Revisar que `RewriteResult` y `RerankResult` sigan estrictamente las convenciones de DTOs del proyecto (inmutabilidad, slots, etc.).

## 5. 🚀 Configuración y Despliegue

- [ ] **Documentación de Variables de Entorno**
  - Agregar las nuevas flags a `apps/backend/.env.example`:
    - `ENABLE_QUERY_REWRITE=true/false`
    - `ENABLE_RERANK=true/false`
    - `RERANK_REL_THRESHOLD=0.5`
