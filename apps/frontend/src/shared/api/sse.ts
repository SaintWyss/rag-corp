/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/api/sse.ts (SSE helpers)
===============================================================================
Responsabilidades:
  - Parsear eventos SSE en formato event/data.
  - Mantener parsing liviano sin dependencias externas.

Colaboradores:
  - features/rag (streaming)
===============================================================================
*/

export type SseEvent = {
  event: string;
  data: string;
};

/**
 * Parsea un bloque SSE (separado por doble \n) en un evento.
 * Retorna null si el bloque es vacío o no tiene data útil.
 */
export function parseSseEvent(raw: string): SseEvent | null {
  if (!raw.trim()) {
    return null;
  }
  const lines = raw.split("\n");
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  const data = dataLines.join("\n");
  if (!data) {
    return null;
  }

  return { event, data };
}
