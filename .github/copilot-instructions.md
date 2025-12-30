# Instrucciones del proyecto (RAG Corp)

## Principios
- Prioridad: calidad, claridad, arquitectura, testabilidad y mantenimiento.
- Cambios incrementales (PRs pequeños). Evitar refactors masivos.
- Aplicar SOLID y separación de responsabilidades con límites claros entre capas.

## Veracidad / No alucinaciones
- No inventar features/tests/carpetas/paths. Si no existe en el repo, marcar como **TODO/Planned**.
- Antes de afirmar rutas/endpoints/comandos: verificar en el código y `compose.yaml`.

## Modo anti-spam
- Nunca pegar archivos completos en el chat.
- Editar archivos con diff/patch. En el chat: solo **archivos tocados + resumen (≤10 bullets) + comandos de validación**.

## Documentación
- `README.md` raíz como portal y `doc/README.md` como índice.
- ADRs en `doc/architecture/decisions/` (usar template 000).
- Diagramas Mermaid en `doc/diagrams/*.md` cuando cambie el flujo/arquitectura.

## Git (seguro)
- No ejecutar git automáticamente.
- Sugerir stage selectivo (`git add -p`) y mensajes claros (Conventional Commits).
