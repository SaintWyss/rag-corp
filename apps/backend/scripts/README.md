# scripts

Llaves de servicio para ejecutar tareas puntuales del backend (bootstrap de admin y export de contratos OpenAPI).

## 🎯 Misión
Este directorio agrupa **scripts CLI** para tareas administrativas y de documentación que conviene ejecutar **fuera del flujo HTTP**.

Recorridos rápidos por intención:
- **Quiero crear el primer admin en la DB** → `create_admin.py` (también: `pnpm admin:bootstrap`)
- **Quiero exportar el OpenAPI a JSON** → `export_openapi.py` (también: `pnpm contracts:export`)

### Qué SÍ hace
- Crea usuarios (por defecto **admin**) directamente en Postgres, de forma **idempotente por email**.
- Exporta el esquema **OpenAPI** desde la app FastAPI a un archivo JSON.
- Permite operaciones operativas sin levantar el servidor HTTP (se ejecuta como proceso puntual).

### Qué NO hace (y por qué)
- No reemplaza flujos de negocio ni endpoints HTTP.
  - **Razón:** estos scripts son tooling; no son parte del contrato público de la API.
  - **Impacto:** si necesitás validaciones/ACL/observabilidad del runtime, usá casos de uso + routers.
- No maneja migraciones de DB.
  - **Razón:** las migraciones son responsabilidad de `alembic/` y del servicio `migrate`.
  - **Impacto:** si la tabla `users`/esquema no existe, primero corré `pnpm db:migrate`.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| `create_admin.py` | Script Python | Crea un usuario (por defecto admin) en `users` con password hasheado (Argon2) y chequeo de existencia por email. |
| `export_openapi.py` | Script Python | Genera `openapi.json` desde `app.api.main` y lo escribe con `indent=2` (UTF-8). |
| `README.md` | Documento | Portada + guía de uso de los scripts de este directorio. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output, con los pasos reales del código.

### `create_admin.py`
- **Input:** flags CLI (`--email`, `--password`, `--role`, `--inactive`) o prompts interactivos si faltan.
- **Proceso:**
  1) Lee `DATABASE_URL` (sin eso corta en fail-fast).
  2) Normaliza email (trim + lower).
  3) Si no hay `--password`, solicita password con `getpass` y confirma.
  4) Abre conexión con `psycopg` y consulta `users` por email.
  5) Si existe, imprime “User already exists …” y termina (idempotencia por email).
  6) Si no existe, genera `uuid4()`, hashea el password con `hash_password(...)` y hace `INSERT` en `users`.
- **Output:** prints de resultado (creado / ya existía) + filas persistidas en Postgres.

Notas operativas:
- El script ajusta `sys.path` para poder importar módulos del backend al ejecutarlo como archivo suelto.
- Si falla por imports (`ModuleNotFoundError`), revisar “Troubleshooting”.

### `export_openapi.py`
- **Input:** `--out <path>`.
- **Proceso:**
  1) Importa la app desde `app.api.main` y resuelve la instancia que expone `.openapi()` (si viene envuelta, la “desenvuelve”).
  2) Genera el schema con `openapi()`.
  3) Escribe JSON con `ensure_ascii=False` e `indent=2`.
- **Output:** archivo JSON en la ruta indicada.

Notas operativas:
- Importar `app.api.main` ejecuta la carga de settings; normalmente requiere `DATABASE_URL` disponible en el entorno.
- El script **no valida** el JSON contra el spec OpenAPI 3.x; solo serializa lo que FastAPI expone.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Operational tooling (fuera de Domain/Application/Interfaces).
- **Recibe órdenes de:** desarrolladores/operadores por CLI (local o dentro de contenedores).
- **Llama a:**
  - Postgres vía `psycopg` (SQL directo) en `create_admin.py`.
  - Composición FastAPI `app.api.main` para generar OpenAPI en `export_openapi.py`.
- **Reglas de límites:**
  - Evitar importar infraestructura pesada o casos de uso para “hacer lo mismo que la API”.
  - Mantener side-effects (conexiones, writes, IO) dentro de `main()`.

## 👩‍💻 Guía de uso (Snippets)

### 1) Crear admin (recomendado: vía docker compose)
```bash
pnpm admin:bootstrap
# interactivo: pide Email + Password si no se pasan flags
