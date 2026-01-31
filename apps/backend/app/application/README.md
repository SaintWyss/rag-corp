# Application Layer (Core Logic)

Esta capa contiene la lógica de coordinación de la aplicación, actuando como intermediario entre la Infraestructura (detalles técnicos) y el Dominio (reglas de negocio puras).

## Estructura

```
application/
├── usecases/                   # Casos de uso (Entry points de negocio)
│   ├── chat/                   # RAG + Chat conversacional
│   ├── documents/              # Resultados y tipos compartidos
│   ├── ingestion/              # Carga y procesamiento de documentos
│   └── workspace/              # Gestión de workspaces
├── context_builder.py          # Ensamblador de contexto para RAG
├── prompt_injection_detector.py # Políticas de seguridad
├── dev_seed_admin.py           # Tarea: Seed de usuario Admin
├── dev_seed_demo.py            # Tarea: Seed de entorno Demo
└── __init__.py                 # Exports públicos
```

## Componentes Compartidos (Shared Logic)

Estos módulos son utilizados por múltiples casos de uso para evitar duplicación de lógica compleja.

### 1. `context_builder.py` (The Grounding Assembler)

Es el responsable de armar el contexto que se envía al LLM.

- **Responsabilidad:** Toma una lista de chunks y los formatea con delimitadores de seguridad.
- **Seguridad:** Aplica sanitización (escapa `---[S#]---` en el contenido) para evitar confusión del modelo.
- **Presupuesto:** Implementa un algoritmo de "mochila" (Knapsack) para llenar el contexto hasta `max_size` sin cortar chunks por la mitad.
- **Grounding:** Genera la sección "FUENTES" alineada con las citas `[S#]` del texto.
- **Future-proofing:** Acepta un `size_counter` inyectable para integrar tiktoken (tokens reales) cuando se necesite.

### 2. `prompt_injection_detector.py` (The Security Guard)

Sistema de defensa en profundidad.

- **Responsabilidad:** Analiza texto no confiable (chunks recuperados) buscando patrones de ataque ("ignora instrucciones", "eres un desarrollador").
- **Estrategia:** No borra datos, pero marca el contenido (`[Contenido sospechoso filtrado]`) o lo mueve al final (`downrank`) según configuración.
- **Patrón:** Rule Engine data-driven (Reglas Regex con pesos).
- **Metadata Keys:** Exports constantes para consistencia en todo el sistema (`METADATA_KEY_RISK_SCORE`, etc.).

## Casos de Uso (Use Cases)

Los casos de uso están organizados por feature en `usecases/`:

### Chat (`usecases/chat/`)

| Use Case                        | Descripción                                       |
| ------------------------------- | ------------------------------------------------- |
| `AnswerQueryUseCase`            | RAG puro (stateless): embedding → retrieval → LLM |
| `AnswerQueryWithHistoryUseCase` | RAG + contexto conversacional + persistencia      |
| `SearchChunksUseCase`           | Solo retrieval (sin LLM) para debugging/UI        |
| `CreateConversationUseCase`     | Inicia una nueva sesión de chat                   |
| `GetConversationHistoryUseCase` | Recupera mensajes de una conversación             |
| `ClearConversationUseCase`      | Limpia el historial de una conversación           |

**Utilities:** `chat_utils.py` contiene helpers para formatear historial (`format_conversation_for_prompt`).

### Ingestion (`usecases/ingestion/`)

| Use Case                          | Descripción                                 |
| --------------------------------- | ------------------------------------------- |
| `UploadDocumentUseCase`           | Sube y persiste un documento (con rollback) |
| `GetDocumentStatusUseCase`        | Consulta el estado de procesamiento         |
| `CancelDocumentProcessingUseCase` | Cancela documentos atascados                |

### Workspace (`usecases/workspace/`)

| Use Case                 | Descripción                         |
| ------------------------ | ----------------------------------- |
| `ListDocumentsUseCase`   | Lista documentos de un workspace    |
| `DeleteDocumentsUseCase` | Elimina documentos con autorización |

## Tareas de Inicialización (Seed Tasks)

Estos scripts se ejecutan al inicio (`main.py`) para preparar el entorno. Siguen el patrón de **Inyección de Dependencias** para no acoplarse a la base de datos real.

- **`dev_seed_admin.py`:** Asegura que exista un super-admin. Útil para desarrollo local y E2E.
  - _Security:_ Tiene un "Kill Switch" que impide correrlo en producción (excepto con E2E override).
- **`dev_seed_demo.py`:** Crea un entorno completo (empleados, workspaces) para demos locales.
  - _Security:_ Solo corre en `app_env == "local"`.

## Principios de la Capa

1.  **Orquestación, no Cálculo:** Esta capa conecta cosas (Repo → Servicio), no hace cálculos matemáticos complejos (eso va al Dominio) ni llamadas HTTP directas (eso va a Infraestructura).
2.  **Fail-Fast:** Las configuraciones inválidas (ej: seed en prod, retrieval sin query) lanzan excepciones inmediatas.
3.  **Observabilidad:** Todos los componentes emiten logs estructurados y métricas de tiempo (`StageTimings`) para debugging.
4.  **Inyección de Dependencias:** Cada use case recibe sus dependencias (repos, services) vía constructor, facilitando testing y composición.
5.  **Contratos Explícitos:** Inputs/Outputs tipados con dataclasses (`@dataclass`), errores tipados (`DocumentError`).
