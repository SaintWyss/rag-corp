# RAG Corp Backend

## 🎯 Misión

Este directorio contiene todo el ecosistema del servidor backend para RAG Corp.
Es el cerebro de la aplicación, encargado de la lógica de negocio, la persistencia de datos, la integración con modelos de IA (LLMs) y la exposición de la API REST.

**Qué SÍ hace:**

- Expone una API HTTP (FastAPI) para el frontend.
- Procesa documentos en segundo plano (Workers).
- Gestiona la base de datos PostgreSQL (con pgvector).

**Qué NO hace:**

- No sirve archivos estáticos del frontend (HTML/JS/CSS).
- No maneja autenticación de navegador (cookies de sesión de UI), usa tokens JWT/API Key.

**Analogía:**
Si toda la aplicación fuera un restaurante de lujo, este directorio es la **Cocina y la Bodega**. Aquí están los chefs (Use Cases), los ingredientes (Data) y los protocolos de seguridad. El Frontend es solo el comedor.

## 🗺️ Mapa del territorio

| Recurso            | Tipo       | Responsabilidad (en humano)                                        |
| :----------------- | :--------- | :----------------------------------------------------------------- |
| `alembic/`         | 📁 Carpeta | Configuración de migraciones de base de datos.                     |
| `app/`             | 📁 Carpeta | **Código Fuente**. El corazón de la aplicación.                    |
| `htmlcov/`         | 📁 Carpeta | Reportes de cobertura de tests (generados).                        |
| `migrations/`      | 📁 Carpeta | Historial de versiones del esquema de base de datos.               |
| `scripts/`         | 📁 Carpeta | Herramientas para desarrolladores (crear admin, exportar OpenAPI). |
| `tests/`           | 📁 Carpeta | Suite de pruebas (Unitarias, Integración, E2E).                    |
| `.env`             | 🧾 Config  | Variables de entorno (secretos, puertos) para local.               |
| `Dockerfile`       | 🧾 Config  | Receta para construir la imagen Docker de producción.              |
| `pytest.ini`       | 🧾 Config  | Configuración del runner de pruebas.                               |
| `requirements.txt` | 🧾 Config  | Dependencias de Python (librerías).                                |

## ⚙️ ¿Cómo funciona por dentro?

El backend es una aplicación **Python 3.10+** modular.

- **Framework Web:** FastAPI (Asíncrono).
- **Base de Datos:** PostgreSQL + pgvector (Soportado por SQLAlchemy 2.0).
- **Cola de Tareas:** Redis Queue (RQ) para procesamiento pesado (PDFs).
- **Arquitectura:** Clean Architecture (Capas concéntricas).

## 👩‍💻 Guía de uso (Snippets)

### Levantar servidor de desarrollo

```bash
# Desde apps/backend/
# Asegúrate de tener el entorno virtual activo y las deps instaladas
pip install -r requirements.txt

# Iniciar Uvicorn con Hot-Reload
uvicorn app.api.main:app --reload --port 8000
```

### Correr pruebas

```bash
# Correr todas las pruebas (rápidas)
pytest

# Correr con reporte de coverage
pytest --cov=app
```

## 🧩 Cómo extender sin romper nada

1.  **Nueva Funcionalidad:** Empieza siempre en `app/application/usecases/`. No escribas lógica en la API ni los controladores.
2.  **Nueva Tabla:** Crea el modelo en `app/infrastructure/db/models.py` y genera la migración con `alembic revision --autogenerate`.
3.  **Nueva Dependencia:** Agrégala a `requirements.txt`.

## 🆘 Troubleshooting

- **Error:** `ModuleNotFoundError: No module named 'app'`
  - **Solución:** Asegúrate de estar ejecutando comandos desde `apps/backend/` y que tu `PYTHONPATH` incluya el directorio actual.
- **Error:** `OperationalError: connection refused` (Postgres)
  - **Solución:** Verifica que Docker esté corriendo (`docker compose up -d db`).

## 🔎 Ver también

- [Código Fuente (App)](./app/README.md)
- [Estrategia de Tests](./tests/README.md)
