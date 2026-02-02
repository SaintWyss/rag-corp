# Migrations (carpeta auxiliar)

## 🎯 Misión
Reservar un espacio para artefactos de migración o puntos de montaje de volúmenes cuando se ejecuta el backend con Docker/local.

**Qué SÍ hace**
- Mantiene un lugar estable para guardar migraciones externas si se usa como volumen.
- Documenta el rol de la carpeta en este repositorio.

**Qué NO hace**
- No contiene scripts de migración en este repo.
- No reemplaza `alembic/versions/`.

**Analogía (opcional)**
- Es un “estante vacío” listo para usarse si el entorno lo necesita.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 📄 `README.md` | Documento | Explica el rol actual de la carpeta. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: uso externo (montaje de volumen o scripts propios del entorno).
- **Proceso**: no hay lógica en el repo.
- **Output**: archivos opcionales fuera del control del código.

Tecnologías/librerías usadas aquí:
- Ninguna (carpeta auxiliar).

Flujo típico:
- Si el entorno monta un volumen, esta carpeta actúa como destino.
- Las migraciones reales del repo viven en `alembic/versions/`.

## 🔗 Conexiones y roles
- Rol arquitectónico: Tooling / soporte operativo.
- Recibe órdenes de: tooling externo (Docker/CI/local).
- Llama a: no aplica.
- Contratos y límites: no contiene lógica ni scripts en este repo.

## 👩‍💻 Guía de uso (Snippets)
```python
from pathlib import Path

migrations_dir = Path(__file__).resolve().parent
assert (migrations_dir / "README.md").exists()
```

## 🧩 Cómo extender sin romper nada
- Si vas a usarla, documenta qué archivos se esperan aquí.
- No mezcles scripts de Alembic en esta carpeta.
- Mantén el README actualizado si cambia su función.

## 🆘 Troubleshooting
- Síntoma: buscás migraciones y no están → Causa probable: están en `alembic/versions/` → Mirar `../alembic/`.
- Síntoma: la carpeta aparece vacía en Docker → Causa probable: volumen montado vacío → Revisar `compose`/config externo.

## 🔎 Ver también
- [Alembic](../alembic/README.md)
- [Backend root](../README.md)
