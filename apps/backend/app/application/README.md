# Application Layer (Core Logic)

Esta capa contiene la lógica de coordinación de la aplicación, actuando como intermediario entre la Infraestructura (detalles técnicos) y el Dominio (reglas de negocio puras).

## Estructura

```
application/
├── usecases/                   # Casos de uso (Entry points de negocio)
├── context_builder.py          # Ensamblador de contexto para RAG
├── rag_retrieval.py            # Pipeline de búsqueda compartido
├── conversations.py            # Helpers para historial de chat
├── prompt_injection_detector.py # Políticas de seguridad
├── dev_seed_admin.py           # Tarea: Seed de usuario Admin
├── dev_seed_demo.py            # Tarea: Seed de entorno Demo
└── __init__.py                 # Exports públicos
```

## Componentes Compartidos (Shared Logic)

Estos módulos son utilizados por múltiples casos de uso para evitar duplicación de lógica compleja.

### 1. `rag_retrieval.py` (The Retrieval Pipeline)

Es el orquestador de búsqueda. No decide _qué decir_, solo _qué encontrar_.

- **Responsabilidad:** Embed Query -> Búsqueda Vectorial (similitud o MMR) -> Construcción de Contexto -> Timings.
- **Diseño:** Pipeline funcional que devuelve un `RagRetrievalResult` agnóstico (sirve para chat, stream, reports).
- **Clave:** Centraliza el manejo de "No hay resultados" (`fallback_answer`) para consistencia en toda la app.

### 2. `context_builder.py` (The Grounding Assembler)

Es el responsable de armar el prompt gigante que se envía al LLM.

- **Responsabilidad:** Toma una lista de chunks y los formatea con delimitadores de seguridad.
- **Seguridad:** Aplica sanitización (escapa `---[S#]---` en el contenido) para evitar confusión del modelo.
- **Presupuesto:** Implementa un algoritmo de "mochila" (Knapsack) para llenar el contexto hasta `MAX_CHARS` sin cortar chunks por la mitad.
- **Grounding:** Genera la sección "FUENTES" alineada con las citas `[S#]` del texto.

### 3. `prompt_injection_detector.py` (The Security Guard)

Sistema de defensa en profundidad.

- **Responsabilidad:** Analiza texto no confiable (chunks recuperados) buscando patrones de ataque ("ignora instrucciones", "eres un pirata").
- **Estrategia:** No borra datos, pero marca el contenido (`[Contenido sospechoso filtrado]`) o lo mueve al final (`downrank`) según configuración.
- **Patrón:** Rule Engine data-driven (Reglas Regex con pesos).

### 4. `conversations.py` (The Memory Manager)

Helpers para gestionar la continuidad del diálogo.

- **Responsabilidad:** Formatea el historial de chat (`Usuario: ... Asistente: ...`) para que el LLM entienda el contexto.
- **Windowing:** Aplica ventana deslizante (ej: últimos 10 mensajes) para proteger el presupuesto de tokens.

## Tareas de Inicialización (Seed Tasks)

Estos scripts se ejecutan al inicio (`main.py`) para preparar el entorno. Siguen el patrón de **Inyección de Dependencias** para no acoplarse a la base de datos real.

- **`dev_seed_admin.py`:** Asegura que exista un super-admin. Útil para desarrollo local y E2E.
  - _Security:_ Tiene un "Kill Switch" que impide correrlo en producción.
- **`dev_seed_demo.py`:** Crea un entorno completo (empleados, workspaces) para demos locales.

## Principios de la Capa

1.  **Orquestación, no Cálculo:** Esta capa conecta cosas (Repo -> Servicio), no hace cálculos matemáticos complejos (eso va al Dominio) ni llamadas HTTP directas (eso va a Infraestructura).
2.  **Fail-Fast:** Las configuraciones inválidas (ej: seed en prod, retrieval sin query) lanzan excepciones inmediatas.
3.  **Observabilidad:** Todos los componentes emiten logs estructurados y métricas de tiempo (`StageTimings`) para debugging.
