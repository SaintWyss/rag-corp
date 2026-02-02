# Layer: Scripts (Tooling)

## 🎯 Misión

Esta carpeta contiene scripts de utilidad y herramientas de línea de comandos (CLI) para desarrolladores y administradores de sistemas.
Son scripts "one-off" que no forman parte del ciclo de vida de la aplicación web, sino que se ejecutan bajo demanda.

**Qué SÍ hace:**

- Inicializa datos administrativos (`create_admin.py`).
- Exporta esquemas de documentación (`export_openapi.py`).
- Facilita tareas de mantenimiento.

**Qué NO hace:**

- No contiene lógica de negocio reutilizable (debe importar de `application` o `infrastructure`).
- No es un punto de entrada de la aplicación en producción.

**Analogía:**
Si la aplicación es un coche de carreras, estos scripts son las herramientas neumáticas y llaves inglesas del equipo de pits.

## 🗺️ Mapa del territorio

| Recurso             | Tipo      | Responsabilidad (en humano)                                             |
| :------------------ | :-------- | :---------------------------------------------------------------------- |
| `create_admin.py`   | 🧰 Script | Crea un usuario administrador en la base de datos (para setup inicial). |
| `export_openapi.py` | 🧰 Script | Genera el archivo `openapi.json` estático sin levantar el servidor.     |

## ⚙️ ¿Cómo funciona por dentro?

Los scripts suelen seguir este patrón:

1.  Configuran el `PYTHONPATH` para poder importar `app`.
2.  Inicializan dependencias mínimas (como `Settings` o DB Pools).
3.  Ejecutan una función de dominio o infraestructura.
4.  Imprimen resultados en stdout.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Tooling / Support.
- **Recibe órdenes de:** Humanos (CLI) o CI/CD pipelines.
- **Llama a:** `app.infrastructure`, `app.identity`, etc.

## 👩‍💻 Guía de uso (Snippets)

### Crear un usuario admin

```bash
# Desde apps/backend/
python -m scripts.create_admin --email admin@ragcorp.com --password secret
```

### Exportar OpenAPI para el frontend

```bash
python -m scripts.export_openapi > openapi.json
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevos Scripts:** Créalos aquí con nombres descriptivos (`fix_data_XYZ.py`).
2.  **Entrada:** Usa `argparse` o `typer` para manejar argumentos.
3.  **Logging:** Usa `print` para feedback de usuario o el `app.logger` si es un proceso desatendido.

## 🆘 Troubleshooting

- **Síntoma:** "ModuleNotFoundError: No module named 'app'".
  - **Causa:** Ejecutaste el script desde dentro de la carpeta `scripts/`.
  - **Solución:** Ejecuta siempre desde la raíz del backend: `python -m scripts.nombre_script`.
