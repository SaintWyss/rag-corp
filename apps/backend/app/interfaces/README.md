# Layer: Interfaces (Adapters In)

## 🎯 Misión

Esta capa contiene los **Adaptadores de Entrada** (Driving Adapters).
Es la "cara" de la aplicación hacia el mundo exterior. Recibe estímulos externos (HTTP requests, comandos CLI, mensajes de cola) y los traduce a comandos que la Capa de Aplicación entienda.

**Qué SÍ hace:**

- Define cómo el mundo habla con nosotros.
- Valida formatos de entrada (JSON, XML).
- Gestiona códigos de estado HTTP (200, 404).

**Qué NO hace:**

- No contiene lógica de negocio.
- No accede a la base de datos directamente (debe usar Use Cases).

**Analogía:**
Son los traductores de la ONU. Traducen "HTTP POST /users" (Idioma Web) a "CreateUserUseCase.execute()" (Idioma Dominio).

## 🗺️ Mapa del territorio

| Recurso | Tipo       | Responsabilidad (en humano)                      |
| :------ | :--------- | :----------------------------------------------- |
| `api/`  | 📁 Carpeta | adaptadores para APIs (HTTP REST, GraphQL, etc). |

## ⚙️ ¿Cómo funciona por dentro?

Sigue el flujo:
`Input Externo` -> `Adaptador (Interface)` -> `DTO` -> `Caso de Uso (Application)`

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Driving Adapters (Hexagon Outside).
- **Llama a:** `app.application` (Use Cases) y `app.domain` (para DTOs).

## 👩‍💻 Guía de uso (Snippets)

### Definir un endpoint

Ver `api/http/README.md`.

## 🧩 Cómo extender sin romper nada

1.  **Nuevo canal:** Si quieres soportar gRPC, crea `interfaces/grpc`.
2.  **CLI:** Si quieres soportar comandos de terminal complejos, crea `interfaces/cli`.

## 🔎 Ver también

- [API HTTP](./api/README.md)
