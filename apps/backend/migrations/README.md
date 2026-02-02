# Migrations Storage

## 🎯 Misión

Este directorio es un **artefacto** relacionado con el volumen de Docker o configuraciones locales antiguas.
Normalmente, los scripts de migración reales residen dentro de `apps/backend/alembic/versions`.

Si esta carpeta está vacía y es propiedad de `root` (por uso de Docker), es seguro ignorarla, pero su presencia indica puntos de montaje de volúmenes.

## 🗺️ Mapa del territorio

| Recurso | Tipo       | Responsabilidad (en humano)                                    |
| :------ | :--------- | :------------------------------------------------------------- |
| `.`     | 📁 Carpeta | Posible punto de montaje de volúmenes Docker o legacy storage. |

## 🔎 Ver también

- [Configuración de Alembic y Versiones Reales](../alembic/README.md)
