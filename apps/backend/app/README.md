# Backend Application Source (`app/`)

## 🎯 Misión

Aquí reside el código fuente de la aplicación, estrictamente organizado siguiendo **Clean Architecture**.
El objetivo es mantener la lógica de negocio (el "qué hace la app") desacoplada de los detalles técnicos (el "cómo lo hace").

**Qué SÍ hace:**

- Define las entidades del negocio (Domain).
- Orquesta los flujos de trabajo (Application).
- Implementa conexiones a bases de datos y servicios externos (Infrastructure).
- Expone la API (Interfaces).

**Qué NO hace:**

- No contiene scripts de despliegue ni configuración de CI/CD.
- No contiene archivos de tests (están en `../tests`).

**Analogía:**
Es como las capas de una cebolla. En el centro está el **Dominio** (intocable), rodeado por la **Aplicación**, y en el borde exterior están la **Infraestructura** y las **Interfaces**. Las dependencias solo apuntan hacia adentro.

## 🗺️ Mapa del territorio

| Recurso           | Tipo       | Responsabilidad (en humano)                                            |
| :---------------- | :--------- | :--------------------------------------------------------------------- |
| `api/`            | 📁 Carpeta | **Composition Root**. Punto de entrada, configuración y arranque.      |
| `application/`    | 📁 Carpeta | **Lógica de Aplicación**. Casos de uso (Use Cases) y orquestación.     |
| `crosscutting/`   | 📁 Carpeta | **Utilidades**. Herramientas compartidas (Logs, Config, Errores).      |
| `domain/`         | 📁 Carpeta | **Negocio Puro**. Entidades y reglas que no cambian por tecnología.    |
| `identity/`       | 📁 Carpeta | **Subdominio de Identidad**. Gestión de usuarios, roles y permisos.    |
| `infrastructure/` | 📁 Carpeta | **Adaptadores Salientes (Infra)**. DB, S3, LLMs, Colas.                |
| `interfaces/`     | 📁 Carpeta | **Adaptadores Entrantes (API)**. Routes, Schemas y Controladores HTTP. |
| `prompts/`        | 📁 Carpeta | **Assets de IA**. Templates de prompts y políticas de sistema.         |
| `worker/`         | 📁 Carpeta | **Procesamiento Async**. Entrypoint para los workers de cola.          |
| `audit.py`        | 🐍 Archivo | Helper global de auditoría (Bridge pattern simplificado).              |
| `container.py`    | 🐍 Archivo | **Inyección de Dependencias**. Fábrica de objetos y cableado.          |
| `context.py`      | 🐍 Archivo | Gestión de contexto por request (User ID, Workspace ID).               |
| `jobs.py`         | 🐍 Archivo | Definición de tareas en background (Jobs de RQ).                       |
| `main.py`         | 🐍 Archivo | Re-exporta la app ASGI para servidores WSGI (Gunicorn).                |

## ⚙️ ¿Cómo funciona por dentro?

El flujo de datos atraviesa las capas:

1.  **Request HTTP** llega a `interfaces/api`.
2.  El controlador invoca un **Use Case** en `application/`.
3.  El Use Case pide datos a un **Repository Interface** (en `domain/`).
4.  En tiempo de ejecución, `container.py` inyecta la implementación real del repositorio (de `infrastructure/`).
5.  El Use Case devuelve una entidad de dominio o un DTO.
6.  El controlador lo transforma a JSON y responde.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Source Root.
- **Recibe órdenes de:** `../tests` (durante pruebas) o el servidor ASGI (Uvicorn).
- **Llama a:** Librerías externas (SQLAlchemy, Pydantic, etc.).

## 👩‍💻 Guía de uso (Snippets)

### Importar componentes entre capas

```python
# Un controlador (Interfaces) importando un Use Case (Application)
from app.application.usecases.chat.answer_query import AnswerQueryUseCase

# Una implementación (Infrastructure) importando una interfaz (Domain)
from app.domain.repositories import DocumentRepository
```

## 🧩 Cómo extender sin romper nada

1.  **Respeta la dirección de dependencias:**
    - Domain NO importa nada (solo estándar).
    - Application solo importa Domain.
    - Infrastructure/Interfaces importan Application y Domain.
2.  **Usa `metrics.py` y `logger.py` de `crosscutting`** para observabilidad uniforme.

## 🔎 Ver también

- [Root README](../README.md)
- [Capa de API (Composition Root)](./api/README.md)
- [Capa de Aplicación (Use Cases)](./application/README.md)
