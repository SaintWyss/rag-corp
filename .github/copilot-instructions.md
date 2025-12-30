# Instrucciones del proyecto (RAG Corp)

- Prioridad: calidad, claridad, arquitectura, testabilidad y mantenimiento.
- Antes de proponer cambios: explicar el estado actual y justificar decisiones.
- Aplicar SOLID, separación de responsabilidades, y límites claros entre capas.
- Preferir cambios incrementales en pasos pequeños (tipo PR), con verificación.
- No introducir dependencias nuevas sin justificar (impacto, beneficio, alternativa).
- Documentar decisiones relevantes como ADRs en doc/decisions/.
- Comentarios estilo “CRC Cards”:
  - En módulos/clases/componentes principales: bloque al inicio con:
    Name, Responsibilities, Collaborators, Notes/Constraints.
  - Evitar comentarios redundantes; priorizar intención y arquitectura.
- Generar documentación en doc/ y mantener README root como “portal” (Quickstart + links).
- Siempre que sea posible, incluir diagramas Mermaid dentro de doc/diagrams/.md para ilustrar arquitectura y flujos.
- Asegurar cobertura de tests adecuada:
- Incluir tests automatizados para nuevas funcionalidades y cambios.
- Realizar revisiones de código (code reviews) para cambios significativos.
- Mantener consistencia con el estilo y convenciones del proyecto.
- Cada vez que se realicen cambios significativos en la arquitectura o diseño hacer git add . y git commit -m "especificar cambios realizados".
