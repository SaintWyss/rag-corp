# Instrucciones del proyecto (RAG Corp)

## Principios
- Prioridad: **calidad, claridad, arquitectura, patrones, testabilidad y mantenimiento**.
- Cambios incrementales (PRs pequeños). Evitar refactors masivos.
- Aplicar **SOLID** y separación de responsabilidades con límites claros entre capas.

## Veracidad / No alucinaciones
- No inventar features/tests/carpetas/paths. Si no existe en el repo, marcar como **TODO/Planned**.
- Antes de afirmar rutas/endpoints/comandos: verificar en el código, en `compose.yaml` y en la documentación existente.
- Si no se puede verificar, **asumir lo mínimo** y dejar la suposición explícita en **1 línea**.


## Modo anti-spam
- Nunca pegar archivos completos en el chat.
- Editar archivos con **diff/patch**.
- En el chat: solo **archivos tocados + resumen (≤10 bullets) + comandos de validación**.


## Modo de trabajo (ejecución directa)
- **Ejecutar** cambios directamente: no preguntar “¿es lo que querés?” ni pedir confirmación.
- **No hacer planeamiento** ni listas de “opciones”, salvo ambigüedad real o riesgo alto.
- Si falta una decisión menor, **elegir la opción más segura y coherente** con el repo y continuar.
- Solo pedir aclaración cuando:
  - haya **ambigüedad bloqueante** (dos interpretaciones igualmente plausibles),
  - implique un **cambio destructivo** (pérdida de datos / compat breaking),
  - o haya **riesgo de seguridad**.
- Entregar el resultado como:
  - **diff/patch**, y en el chat: **archivos tocados + resumen (≤10 bullets) + comandos de validación**.


## Documentación
- `README.md` raíz como portal y `doc/README.md` como índice.
- Arquitectura en `doc/architecture/overview.md`.
- API en `doc/api/http-api.md`.
- Datos en `doc/data/postgres-schema.md`.
- Runbook en `doc/runbook/local-dev.md`.
- Si un cambio impacta docs, **actualizarlas en el mismo PR**.


## Git (flujo)
- Trabajar siempre en una **rama por hito** (`feat/hX-...` / `fix/hX-...`).
- Crear/actualizar un **registro del hito** en `doc/hitos/<rama>.md` con:
  - objetivo, cambios, decisiones, comandos, y checklist de validación.
- Hacer **un commit final** por hito (salvo que se requiera dividir por CI o revertir).
- Sugerir stage selectivo (`git add -p`) y mensajes claros (**Conventional Commits**).
- No hacer `commit/push` automáticamente: solo indicar comandos.
- Al finalizar un hito, crear un **Pull Request** con:
  - descripción del cambio,
  - link al registro del hito,
  - checklist de validación.