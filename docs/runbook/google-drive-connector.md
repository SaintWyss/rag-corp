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
alembic upgrade head  # Aplica todas las migraciones incluyendo 010_external_source_metadata
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

---

## Sync

### Trigger manual

```bash
curl -X POST https://app.example.com/v1/workspaces/{workspace_id}/connectors/sources/{source_id}/sync
```

Respuesta exitosa:

```json
{
  "source_id": "...",
  "stats": {
    "files_found": 10,
    "files_ingested": 5,
    "files_updated": 2,
    "files_skipped": 3,
    "files_errored": 0
  }
}
```

### Sync Update-Aware

El connector implementa **sincronización update-aware** (v2), que detecta cambios
en archivos de Google Drive sin re-ingestar todo el contenido:

| Situación                       | Acción           | Descripción                                             |
| ------------------------------- | ---------------- | ------------------------------------------------------- |
| Archivo nuevo (no existe en DB) | `CREATE`         | Se ingesta normalmente y se guarda la metadata externa  |
| Archivo existente sin cambios   | `SKIP_UNCHANGED` | Se omite (idempotente)                                  |
| Archivo existente con cambios   | `UPDATE`         | Se re-ingesta: borrar chunks antiguos → insertar nuevos |

#### Detección de cambios

Se usan dos campos para detectar si un archivo cambió:

1. **`md5Checksum`** (preferido): Hash del contenido reportado por Drive.
   - Solo disponible para archivos binarios (PDF, imágenes, etc.).
   - No disponible para Google Docs, Sheets, Slides.

2. **`modifiedTime`** (fallback): Timestamp de última modificación.
   - Siempre disponible.
   - Puede generar falsos positivos (ej: cambio de permisos sin cambio de contenido).

#### Métricas de observabilidad

```
rag_connector_files_created_total    # Archivos nuevos ingestados
rag_connector_files_updated_total    # Archivos actualizados (re-ingestados)
rag_connector_files_skipped_unchanged_total  # Archivos omitidos (sin cambios)
```

### Idempotencia

Los documentos ingestados desde Google Drive tienen un `external_source_id` con formato
`gdrive:{file_id}`. Si el archivo ya fue ingestado (misma `external_source_id` + `workspace_id`),
el sync lo detecta y decide según la metadata externa si debe:

- **Skipear** (sin cambios)
- **Actualizar** (cambios detectados)

### Tipos de archivo soportados (MVP)

- Google Docs → exporta como texto plano
- Google Sheets → exporta como CSV
- Google Slides → exporta como texto plano
- text/plain, text/csv, text/markdown → descarga directa
- application/pdf → descarga directa

Otros tipos MIME se omiten (skipped).

### Límites

- Máximo 100 archivos por ejecución de sync (safety guard)
- Timeout de 30s por operación HTTP contra Google Drive API

### Cursor (delta sync)

El connector usa Google Drive Changes API para sincronización incremental.
El cursor se almacena como JSON en `connector_sources.cursor_json`.
En la primera sincronización se listan todos los archivos y se obtiene el `startPageToken`.
En syncs posteriores solo se procesan los cambios desde el último cursor.

---

## Troubleshooting de Sync

### Datos obsoletos (stale data)

**Síntoma**: Un archivo fue modificado en Drive pero la versión en RAG Corp no se actualizó.

**Causas posibles**:

1. El cursor está muy atrasado (>24h sin sync).
2. Google Drive Changes API tiene un delay (hasta 1-2 minutos).
3. El archivo no tiene `modifiedTime` actualizado (raro).

**Solución**:

1. Ejecutar sync manualmente.
2. Si persiste, resetear el cursor (borrar `cursor_json` del source y re-sincronizar).

### Rate limiting (429 errors)

**Síntoma**: Sync falla con error 429 o "quota exceeded".

**Causas**:

- Demasiados syncs en paralelo.
- Workspace con muchos archivos (>1000).

**Solución**:

1. Backoff exponencial con jitter ya implementado en `GoogleDriveClient` (hasta 4 reintentos, respeta `Retry-After`).
2. Espaciar syncs (mínimo 5 minutos entre ejecuciones).
3. Solicitar aumento de cuota en Google Cloud Console.
4. Ajustar settings si es necesario:
   - `CONNECTOR_RETRY_MAX_ATTEMPTS` (default: 4)
   - `CONNECTOR_RETRY_BASE_DELAY_S` (default: 1.0)
   - `CONNECTOR_RETRY_MAX_DELAY_S` (default: 30.0)

### Sync lock stuck (source stuck en SYNCING)

**Síntoma**: Source permanece en status `syncing` indefinidamente, syncs posteriores se skipean.

**Causa**: El sync anterior crasheó sin liberar el lock (CAS status-based).

**Solución**:

```sql
-- Resetear status manualmente
UPDATE connector_sources
SET status = 'error', updated_at = now()
WHERE id = '<source_id>' AND status = 'syncing';
```

Luego re-ejecutar sync. Monitorear métrica `rag_connector_sync_locked_total` para detectar colisiones recurrentes.

### Archivo demasiado grande (ConnectorFileTooLargeError)

**Síntoma**: Algunos archivos no se sincronizan, log muestra "file too large, skipping".

**Causa**: El archivo excede `MAX_CONNECTOR_FILE_MB` (default: 25 MB).

**Solución**:

1. Esto es un safety guard anti-OOM. Los archivos grandes se skipean silenciosamente.
2. Ajustar `MAX_CONNECTOR_FILE_MB` si se requiere ingestar archivos más grandes.
3. Verificar que los archivos ignorados no son críticos para el workspace.

### Re-sync forzado (clear state)

Para forzar una re-sincronización completa:

```sql
-- Resetear cursor del source
UPDATE connector_sources
SET cursor_json = NULL
WHERE id = '<source_id>';

-- (Opcional) Limpiar documentos del source para re-ingestar desde cero
UPDATE documents
SET deleted_at = NOW()
WHERE source LIKE 'google_drive:<source_id>%';
```

Luego ejecutar sync manualmente.

---

## Hardening P0

Funcionalidades de resiliencia implementadas para producción:

| Feature | Descripción | Config |
| --- | --- | --- |
| **Retry + Backoff** | Reintentos exponenciales con jitter para 429/5xx/timeouts. Respeta `Retry-After`. | `CONNECTOR_RETRY_*` |
| **Error Classification** | Errores permanentes (401/403/404) no reintentan. Transitorios (429/5xx/timeout) sí. | — |
| **Streaming Download** | Descarga en chunks de 64KB, no carga archivo completo en RAM. | — |
| **Max Size Guard** | Archivos > `MAX_CONNECTOR_FILE_MB` se skipean (anti-OOM). | `MAX_CONNECTOR_FILE_MB` |
| **Incremental SHA-256** | Hash calculado durante streaming sin carga extra de RAM. | — |
| **Per-source Sync Lock** | CAS atómico: solo un sync por source simultáneo. `try_set_syncing()`. | — |
| **Métricas Prometheus** | `rag_connector_api_retries_total`, `rag_connector_api_failures_total`, `rag_connector_sync_locked_total` | — |

### Métricas de observabilidad

```promql
# Tasa de retries por provider
rate(rag_connector_api_retries_total{provider="google_drive"}[5m])

# Failures por razón
sum by (reason) (increase(rag_connector_api_failures_total{provider="google_drive"}[1h]))

# Colisiones de sync lock
increase(rag_connector_sync_locked_total[1h])
```

---

## Schema de metadatos externos

Los documentos sincronizados desde Google Drive almacenan metadata adicional:

| Campo                      | Tipo        | Descripción                              |
| -------------------------- | ----------- | ---------------------------------------- |
| `external_source_id`       | TEXT        | `gdrive:{file_id}` — identificador único |
| `external_source_provider` | TEXT        | `google_drive`                           |
| `external_modified_time`   | TIMESTAMPTZ | Timestamp de Drive                       |
| `external_etag`            | TEXT        | `md5Checksum` de Drive (si disponible)   |
| `external_mime_type`       | TEXT        | MIME type reportado por Drive            |
| `content_hash`             | TEXT        | SHA-256 del contenido descargado         |

Estos campos se usan para:

1. Idempotencia (evitar duplicados).
2. Detección de cambios (update-aware sync).
3. Trazabilidad (origen del documento).
4. Verificación de integridad (`content_hash`).
