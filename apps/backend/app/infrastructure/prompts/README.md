# Infra: Prompt Loader

## 🎯 Misión

Carga plantillas de texto (prompts) desde el sistema de archivos.
Permite separar el código Python de los textos de ingeniería de prompts, facilitando su edición sin redeployar código (idealmente).

**Qué SÍ hace:**

- Lee archivos `.txt` o `.j2` (Jinja2) de la carpeta `app/prompts`.
- Maneja caché simple para no leer disco en cada request.

**Qué NO hace:**

- No renderiza las variables (eso lo hace `application/context_builder` o similar usando formateo de strings).

## 🗺️ Mapa del territorio

| Recurso     | Tipo       | Responsabilidad (en humano)                |
| :---------- | :--------- | :----------------------------------------- |
| `loader.py` | 🐍 Archivo | Clase `PromptLoader` que lee los archivos. |

## ⚙️ ¿Cómo funciona por dentro?

Simplemente abre el archivo en `app/prompts/{name}.txt` y devuelve el contenido como string.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure Resource Access.
- **Consume:** Archivos en `app/prompts`.

## 👩‍💻 Guía de uso (Snippets)

### Cargar un prompt

```python
loader = PromptLoader()
template = loader.load("rag_answer/system_prompt.txt")
```

## 🔎 Ver también

- [Carpeta de Prompts (Assets)](../../prompts/README.md)
