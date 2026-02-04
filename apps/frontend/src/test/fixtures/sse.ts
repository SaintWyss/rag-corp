/**
===============================================================================
TARJETA CRC - apps/frontend/src/test/fixtures/sse.ts (SSE fixtures)
===============================================================================
Responsabilidades:
  - Proveer fixtures reutilizables para streams SSE.
===============================================================================
*/

export const SAMPLE_CHAT_STREAM = [
  'event: sources\ndata: {"sources":[{"chunk_id":"c1","content":"Doc 1"}],"conversation_id":"conv-1"}\n\n',
  'event: token\ndata: {"token":"Hola"}\n\n',
  'event: token\ndata: {"token":" mundo"}\n\n',
  'event: done\ndata: {"answer":"Hola mundo","conversation_id":"conv-1"}\n\n',
];
