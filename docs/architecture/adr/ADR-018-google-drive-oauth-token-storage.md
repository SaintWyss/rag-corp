# ADR-018: Google Drive Connector — OAuth + Encrypted Token Storage

## Estado

**Aceptado** (2026-02)

## Contexto

RAG Corp necesita sincronizar documentos desde Google Drive hacia workspaces.
Para acceder al Drive de un usuario, requerimos OAuth 2.0 con almacenamiento
seguro del refresh_token (larga duración, equivalente a credenciales).

### Opciones evaluadas

| Opción                         | Pros                                | Contras                                |
| ------------------------------ | ----------------------------------- | -------------------------------------- |
| Token en claro en DB           | Simple                              | Riesgo crítico si hay data breach      |
| Vault externo (HashiCorp/KMS)  | Máxima seguridad                    | Complejidad operacional, latencia      |
| **Fernet en app + clave env**  | Buena seguridad, simple, auditable  | Rotación manual de clave               |
| OAuth sin almacenamiento       | Sin riesgo de tokens                | Requiere re-auth en cada sync          |

## Decisión

### 1. OAuth 2.0 Authorization Code Flow

- Scopes: `drive.readonly` + `userinfo.email`
- `access_type=offline` + `prompt=consent` para obtener refresh_token
- State parameter con JSON (`workspace_id` + `provider`) para prevenir CSRF

### 2. Cifrado de tokens con Fernet (AES-128-CBC + HMAC-SHA256)

- **Puerto**: `TokenEncryptionPort` en dominio (Protocol)
- **Implementación**: `FernetTokenEncryption` en infraestructura
- **Clave**: Variable de entorno `CONNECTOR_ENCRYPTION_KEY` (Fernet key base64)
- **Fail-fast**: Si la clave falta o es inválida, la app no arranca (ValueError en construcción)

### 3. Modelo de datos

- Tabla `connector_accounts` con unique constraint `(workspace_id, provider)`
- Columna `encrypted_refresh_token TEXT` — solo ciphertext
- Upsert idempotente: re-autenticar sobreescribe la cuenta anterior

### 4. Endpoints

| Método | Path                                                   | Descripción            |
| ------ | ------------------------------------------------------ | ---------------------- |
| GET    | `/v1/workspaces/{id}/connectors/google-drive/auth/start`    | Inicia flujo OAuth     |
| GET    | `/v1/workspaces/{id}/connectors/google-drive/auth/callback` | Procesa callback OAuth |
| GET    | `/v1/workspaces/{id}/connectors/google-drive/account`       | Estado de cuenta       |

### 5. Seguridad

- Refresh token **nunca** se expone en API responses ni logs
- Solo `email_domain` se logea (no PII completa)
- La clave de cifrado se rota manualmente (ver runbook)
- `redirect_uri` parametrizado por workspace_id para validación estricta

## Consecuencias

### Positivas
- Tokens protegidos at-rest con criptografía simétrica estándar
- Clean Architecture respetada: dominio define puertos, infra implementa
- Upsert idempotente simplifica re-autenticación
- Fail-fast previene arranque con configuración insegura

### Negativas
- Rotación de clave requiere re-cifrar todos los tokens (procedimiento manual)
- Sin revocación automática de tokens al desconectar cuenta (TODO: Commit 3)
- Sin soporte multi-proveedor aún (extensible vía `ConnectorProvider` enum)

## Referencias

- [Google OAuth 2.0 for Server-Side Apps](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Fernet Specification](https://github.com/fernet/spec/blob/master/Spec.md)
- ADR-001: Clean Architecture
