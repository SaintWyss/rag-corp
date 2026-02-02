# Infra: PostgreSQL Repositories

## 🎯 Misión

Implementación de persistencia "Grade A" para producción usando PostgreSQL.
Aprovecha características avanzadas como **pgvector** para búsqueda semántica e índices JSONB.

**Qué SÍ hace:**

- CRUD completo de entidades.
- Búsqueda vectorial (`<->` operator de pgvector).
- Mapeo manual SQL -> Objetos de Dominio (Data Mapper pattern).

**Qué NO hace:**

- No usa ORM pesado (SQLAlchemy ORM) para consultas, usa estilo Core/Raw para performance y control explícito.

**Analogía:**
Es el bibliotecario meticuloso que guarda cada libro en su estante exacto y sabe buscar por similitud de contenido.

## 🗺️ Mapa del territorio

| Recurso            | Tipo       | Responsabilidad (en humano)                                  |
| :----------------- | :--------- | :----------------------------------------------------------- |
| `audit_event.py`   | 🐍 Archivo | Persistencia de trazas de auditoría.                         |
| `document.py`      | 🐍 Archivo | **Repositorio Complejo**. CRUD de Docs + Chunks vectoriales. |
| `user.py`          | 🐍 Archivo | Gestión de usuarios (Tabla `users`).                         |
| `workspace.py`     | 🐍 Archivo | Gestión de workspaces.                                       |
| `workspace_acl.py` | 🐍 Archivo | Gestión de permisos (Tabla `workspace_acl`).                 |

## ⚙️ ¿Cómo funciona por dentro?

1.  Obtiene conexión (`get_session`).
2.  Ejecuta SQL parametrizado.
3.  Convierte filas (`Row`) a `Entity` o `DTO`.
4.  Cierra sesión (bloque `finally`).

### pgvector

En `document.py`, usamos la extensión vector para buscar chunks similares.

```sql
SELECT * FROM chunks ORDER BY embedding <-> [vector] LIMIT 5
```

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Production Infrastructure.
- **Llama a:** `app.infrastructure.db.pool`.

## 👩‍💻 Guía de uso (Snippets)

### Ejemplo de uso interno (Document Repo)

```python
async with get_session() as conn:
    await conn.execute("INSERT INTO documents ...")
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevas Queries:** Escribe SQL explícito. Evita Magic ORM.
2.  **Transacciones:** Si una operación requiere atomicidad, usa `async with conn.transaction():`.

## 🆘 Troubleshooting

- **Síntoma:** Error "relation 'vector' does not exist".
  - **Causa:** No se instaló la extensión pgvector en la DB. (Revisa migraciones).

## 🔎 Ver también

- [Database Pool](../../db/README.md)
