# Google Drive Connector — Runbook

## Configuración inicial

### 1. Variables de entorno requeridas

```bash
# Google OAuth (obtener desde Google Cloud Console > APIs & Services > Credentials)
GOOGLE_OAUTH_CLIENT_ID=<client-id>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<client-secret>
GOOGLE_OAUTH_REDIRECT_URI=https://app.example.com/v1/workspaces/{workspace_id}/connectors/google-drive/auth/callback

# Clave de cifrado para tokens (Fernet, AES-128-CBC + HMAC-SHA256)
CONNECTOR_ENCRYPTION_KEY=<fernet-key-base64>
```

### 2. Generar clave de cifrado

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> **IMPORTANTE**: Guardar la clave en un lugar seguro (secret manager, vault).
> Sin esta clave, los refresh tokens almacenados no se pueden descifrar.

### 3. Crear credenciales OAuth en Google Cloud

1. Ir a [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Crear un "OAuth 2.0 Client ID" tipo "Web application"
3. Agregar el redirect URI configurado en `GOOGLE_OAUTH_REDIRECT_URI`
4. Habilitar las APIs: Google Drive API, Google People API (o userinfo)
5. Copiar Client ID y Client Secret a las variables de entorno

### 4. Migración de base de datos

```bash
cd apps/backend
alembic upgrade head  # Aplica 007_connector_sources + 008_connector_accounts
```

---

## Rotación de clave de cifrado

### Cuándo rotar

- Sospecha de compromiso de la clave
- Rotación periódica (recomendado: cada 90 días)
- Cambio de personal con acceso a secrets

### Procedimiento

1. **Generar nueva clave**:
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Re-cifrar tokens existentes** (script de migración):
   ```python
   from cryptography.fernet import Fernet

   old_key = "OLD_KEY_HERE"
   new_key = "NEW_KEY_HERE"

   old_fernet = Fernet(old_key.encode())
   new_fernet = Fernet(new_key.encode())

   # Para cada cuenta en connector_accounts:
   # plaintext = old_fernet.decrypt(row.encrypted_refresh_token.encode()).decode()
   # new_ciphertext = new_fernet.encrypt(plaintext.encode()).decode()
   # UPDATE connector_accounts SET encrypted_refresh_token = new_ciphertext WHERE id = row.id
   ```

3. **Actualizar variable de entorno** `CONNECTOR_ENCRYPTION_KEY` con la nueva clave

4. **Restart de la aplicación** (la clave se lee al iniciar)

5. **Verificar**: Ejecutar un sync de prueba para confirmar que los tokens se descifran correctamente

> **ROLLBACK**: Si falla, restaurar la clave anterior. Los tokens se re-cifraron
> in-place, así que se necesita la clave que corresponda a los tokens actuales en DB.

---

## Troubleshooting

### Error: "CONNECTOR_ENCRYPTION_KEY is required"

La app no arranca. Configurar la variable de entorno con una clave Fernet válida.

### Error: "CONNECTOR_ENCRYPTION_KEY is invalid (not a valid Fernet key)"

La clave no tiene formato Fernet válido. Regenerar con el comando de §2.

### Error: "Failed to decrypt token"

La clave actual no coincide con la que se usó para cifrar. Verificar que
`CONNECTOR_ENCRYPTION_KEY` sea la misma clave usada al vincular la cuenta.

### Error: "OAuth state workspace_id mismatch"

El callback recibió un `state` que no corresponde al workspace en la URL.
Posible CSRF o redirect_uri mal configurado.

### Error: "token exchange failed"

Google rechazó el authorization code. Causas comunes:
- Code expirado (válido ~10 min)
- `redirect_uri` no coincide con lo configurado en Google Cloud Console
- Client ID/Secret incorrectos
