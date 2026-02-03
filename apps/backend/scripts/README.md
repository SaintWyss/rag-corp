# scripts
Como **llaves de servicio**: ejecutan tareas puntuales fuera del flujo HTTP.

## 🎯 Misión
Este directorio agrupa scripts CLI para operaciones administrativas y de documentación que conviene ejecutar como procesos puntuales (no como endpoints).

### Qué SÍ hace
- Crea usuarios de forma idempotente en Postgres (`create_admin.py`).
- Exporta el OpenAPI desde la app FastAPI (`export_openapi.py`).
- Permite tareas operativas sin levantar la API completa.

### Qué NO hace (y por qué)
- No reemplaza flujos de negocio.
  - Razón: los contratos públicos viven en HTTP/use cases.
  - Consecuencia: los scripts son tooling, no API pública.
- No ejecuta migraciones.
  - Razón: las migraciones se gestionan con Alembic.
  - Consecuencia: si falta schema, primero correr Alembic.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía de scripts operativos. |
| `create_admin.py` | Script Python | Crea un usuario (default admin) en `users` con password hasheado. |
| `export_openapi.py` | Script Python | Genera `openapi.json` desde la app FastAPI. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **create_admin.py**
  - Input: `--email`, `--password`, `--role`, `--inactive` (o prompts interactivos).
  - Proceso: valida `DATABASE_URL`, normaliza email, hashea password y hace `INSERT` si no existe.
  - Output: imprime “Created user …” o “User already exists …”.
- **export_openapi.py**
  - Input: `--out <path>`.
  - Proceso: importa `app.api.main.app`, genera schema y lo escribe como JSON.
  - Output: archivo JSON con el OpenAPI.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Operational tooling.
- **Recibe órdenes de:** CLI local o CI.
- **Llama a:** Postgres (create_admin) y FastAPI app (export_openapi).
- **Reglas de límites:** evitar lógica de negocio; usar APIs estables del runtime.

## 👩‍💻 Guía de uso (Snippets)
```bash
# Crear admin (interactivo)
python scripts/create_admin.py
```

```bash
# Crear admin con flags
python scripts/create_admin.py --email admin@corp.com --password "Secret" --role admin
```

```bash
# Exportar OpenAPI
python scripts/export_openapi.py --out /tmp/openapi.json
```

## 🧩 Cómo extender sin romper nada
- Si un script necesita dependencias del runtime, obtenelas desde `app/container.py` (no instancies infra a mano).
- Mantené los scripts idempotentes cuando escriban en DB (ej. por email/ID).
- Documentá variables de entorno requeridas en este README.
- Tests: unit en `apps/backend/tests/unit/`, integration si toca DB en `apps/backend/tests/integration/`, e2e si integra con API completa en `apps/backend/tests/e2e/`.

## 🆘 Troubleshooting
- **Síntoma:** `DATABASE_URL is required`.
  - **Causa probable:** variable de entorno ausente.
  - **Dónde mirar:** `.env` y entorno de ejecución.
  - **Solución:** exportar `DATABASE_URL` y reintentar.
- **Síntoma:** `ModuleNotFoundError: No module named 'app'`.
  - **Causa probable:** cwd o `PYTHONPATH` incorrecto.
  - **Dónde mirar:** `pwd` y `sys.path`.
  - **Solución:** ejecutar desde `apps/backend/`.
- **Síntoma:** export de OpenAPI falla por settings.
  - **Causa probable:** `app.api.main` requiere settings/DB no disponibles.
  - **Dónde mirar:** logs del import en `export_openapi.py`.
  - **Solución:** setear variables requeridas o usar un entorno de dev.
- **Síntoma:** usuario no se crea pero no hay error.
  - **Causa probable:** el email ya existe.
  - **Dónde mirar:** salida del script.
  - **Solución:** usar otro email o borrar el usuario en DB.

## 🔎 Ver también
- `../alembic/README.md`
- `../app/api/README.md`
- `../app/container.py`
- `../tests/README.md`
