# Test: E2E (End-to-End)

## 🎯 Misión

Smoke tests o flujos críticos completos que simulan a un usuario real o cliente externo.
Valida que "todo el sistema junto" funcione.

**Qué SÍ hace:**

- Flujo completo: Login -> Subir Doc -> Preguntar -> Respuesta.

**Qué NO hace:**

- No testea casos borde finos (eso es para unitarios).

## 🗺️ Mapa del territorio

| Recurso            | Tipo       | Responsabilidad (en humano)      |
| :----------------- | :--------- | :------------------------------- |
| `test_health.py`   | 🐍 Archivo | Verifica `/healthz` y `/readyz`. |
| `test_flow_rag.py` | 🐍 Archivo | Flujo crítico de RAG.            |

## ⚙️ ¿Cómo funciona por dentro?

Usa `TestClient` o `httpx` contra la instancia levantada de la aplicación.
Es lo más cercano a producción.

## 🔎 Ver también

- [Tests Hub](../README.md)
