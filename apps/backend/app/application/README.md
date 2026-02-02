# Layer: Application (Orchestration & Use Cases)

## 🎯 Misión

Esta capa contiene la **Lógica de la Aplicación**, es decir, los flujos de trabajo específicos que satisfacen los requerimientos del usuario.
Aquí se orquestan los componentes del Dominio y se utilizan los servicios de Infraestructura para lograr un objetivo concreto (ej: "Subir un documento", "Responder una pregunta").

**Qué SÍ hace:**

- Define Casos de Uso (Use Cases) como comandos ejecutables.
- Orquesta: llama al repo, llama al servicio de IA, guarda resultados.
- Implementa lógica de defensa: Rate Limiting de aplicación, detección de inyección de prompts.
- Prepara el contexto para el LLM (`context_builder.py`).

**Qué NO hace:**

- No contiene endpoints HTTP ni conoce FastAPI.
- No implementa SQL (eso es infra).
- No define las entidades (eso es dominio).

**Analogía:**
Es el Director de Orquesta. No toca el violín (Dominio) ni construye el teatro (Infra), pero les dice cuándo entrar y salir para crear la sinfonía.

## 🗺️ Mapa del territorio

| Recurso                        | Tipo       | Responsabilidad (en humano)                                                      |
| :----------------------------- | :--------- | :------------------------------------------------------------------------------- |
| `usecases/`                    | 📁 Carpeta | **Catálogo de Acciones**. Contiene todos los casos de uso agrupados por feature. |
| `context_builder.py`           | 🐍 Archivo | Ensambla chunks de texto recuperados para formar el prompt del LLM.              |
| `conversations.py`             | 🐍 Archivo | Lógica para gestión de hilos de conversación (memoria).                          |
| `prompt_injection_detector.py` | 🐍 Archivo | Capa de seguridad que analiza inputs buscando ataques al LLM.                    |
| `query_rewriter.py`            | 🐍 Archivo | Mejora la query del usuario usando IA antes de buscar.                           |
| `rate_limiting.py`             | 🐍 Archivo | Lógica de negocio para cuotas de uso (Tokens/Requests).                          |
| `reranker.py`                  | 🐍 Archivo | Reordena resultados de búsqueda vectorial para mayor precisión.                  |
| `dev_seed_admin.py`            | 🐍 Archivo | Tarea para crear usuario admin inicial.                                          |
| `dev_seed_demo.py`             | 🐍 Archivo | Tarea para poblar datos de demo.                                                 |

## ⚙️ ¿Cómo funciona por dentro?

El patrón principal es el **Command Pattern** (Use Cases).
Casi toda acción del sistema es una clase con un método `.execute(input_dto)`.

Componentes de Soporte RAG:

1.  **Query Rewriter:** Usuario dice "¿y de vacaciones?", reescribe a "¿Cuál es la política de vacaciones?".
2.  **Reranker:** Toma 20 chunks top-k vectoriales y usa un modelo Cross-Encoder para elegir los 5 mejores reales.
3.  **Context Builder:** Empaqueta esos 5 chunks en un prompt seguro cuidando el límite de tokens.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Application Layer.
- **Recibe órdenes de:** `interfaces/api` y `worker`.
- **Llama a:** `domain` (Entidades) e `infrastructure` (Implementaciones de repos).

## 👩‍💻 Guía de uso (Snippets)

### Usar el Context Builder

```python
from app.application.context_builder import ContextBuilder

builder = ContextBuilder()
context_str = builder.build(
    chunks=[chunk1, chunk2],
    max_tokens=2000
)
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevo flujo:** Crea un Use Case en `usecases/`.
2.  **Lógica compleja compartida:** Si una lógica se repite (ej. calcular precio de tokens), extráela a un archivo en esta carpeta raíz (como `rate_limiting.py`).

## 🆘 Troubleshooting

- **Síntoma:** El LLM alucina respuestas.
  - **Causa Probable:** El `ContextBuilder` no está filtrando bien o el `Reranker` está fallando.
  - **Qué mirar:** Logs de `context_builder.py`.

## 🔎 Ver también

- [Casos de Uso (Detalle)](./usecases/README.md)
