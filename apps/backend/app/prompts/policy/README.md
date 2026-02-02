# Policy Prompts

## 🎯 Misión
Definir el contrato de seguridad global que se antepone a todos los prompts del sistema.

**Qué SÍ hace**
- Establece reglas no negociables (seguridad, fuentes, evidencia).
- Se incluye automáticamente antes del template de respuesta.

**Qué NO hace**
- No contiene lógica de ejecución.
- No define prompts específicos de tarea (eso está en `rag_answer/`).

**Analogía (opcional)**
- Es el “reglamento interno” que todos deben cumplir.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 📄 `README.md` | Documento | Esta documentación. |
| 📄 `secure_contract_es.md` | Documento | Contrato de seguridad en español. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: `PromptLoader` carga policy + template.
- **Proceso**: policy se concatena antes del prompt versionado.
- **Output**: prompt final con reglas globales aplicadas.

Tecnologías/librerías usadas aquí:
- Markdown con frontmatter YAML.

## 🔗 Conexiones y roles
- Rol arquitectónico: Static Assets / Configuration.
- Recibe órdenes de: `PromptLoader` (infra).
- Llama a: no aplica.
- Contratos y límites: policy debe ser coherente con el uso de fuentes `[S#]`.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v1", capability="rag_answer")
policy_plus_template = loader.get_template()
```

## 🧩 Cómo extender sin romper nada
- Mantén el contrato corto y claro; evita contradicciones.
- Versiona cambios si afectan el comportamiento esperado.
- Actualiza tests o checks manuales si cambias reglas críticas.

## 🆘 Troubleshooting
- Síntoma: respuestas sin “Fuentes” → Causa probable: policy/prompt desalineado → Revisar `secure_contract_es.md`.
- Síntoma: prompt loader falla → Causa probable: frontmatter inválido → Revisar YAML.

## 🔎 Ver también
- [Prompts](../README.md)
- [RAG Answer prompts](../rag_answer/README.md)
