# Infrastructure Storage Layer

## 🎯 Propósito y Rol

Este paquete (`infrastructure/storage`) implementa la persistencia de archivos físicos (Blob Storage).
Su responsabilidad es abstraer los detalles del proveedor (S3, MinIO) y exponer una interfaz limpia al dominio, manejando la complejidad de redes, streams y seguridad.

---

## 🧩 Componentes Principales

### 1. El Adaptador (Facade)

| Archivo              | Rol         | Descripción                                                              |
| :------------------- | :---------- | :----------------------------------------------------------------------- |
| `s3_file_storage.py` | **Adapter** | Implementa `FileStoragePort`. Conecta con AWS S3 o MinIO usando `boto3`. |
| `__init__.py`        | **Export**  | Expone las clases principales y limpia el namespace.                     |

### 2. Manejo de Errores (Safety)

| Archivo     | Rol            | Descripción                                                                                                                                                          |
| :---------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `errors.py` | **Exceptions** | Traduce errores de `botocore` (ClientError) a errores de dominio (`StorageNotFoundError`, `StoragePermissionError`). Evita que capas superiores dependan de `boto3`. |

---

## 🛠️ Arquitectura y Features

### Streaming Eficiente

El método `upload_file` acepta `BinaryIO` (streams).

- **Por qué**: Permite subir archivos de gigabytes sin cargarlos en memoria RAM.
- **Cómo**: Usa `upload_fileobj` de boto3 internamente.

### Presigned URLs

Implementamos `generate_presigned_url`.

- **Qué es**: Una URL temporal firmada criptográficamente.
- **Ventaja**: El frontend puede descargar el archivo directamente desde S3/MinIO, liberando al backend de actuar como proxy de tráfico pesado.

### Fail-Fast Configuration

El adaptador valida la existencia de bucket y credenciales al instanciarse. Si falta algo, explota con `StorageConfigurationError` al inicio, no en runtime.

---

## 🚀 Guía de Uso

```python
# Inyección (normalmente vía container.py)
adapter = S3FileStorageAdapter(config=S3Config(...))

# 1. Subir archivo (Stream)
with open("large_video.mp4", "rb") as f:
    adapter.upload_file("videos/video1.mp4", f, content_type="video/mp4")

# 2. Generar link de descarga (seguro)
url = adapter.generate_presigned_url("videos/video1.mp4", expires_in_seconds=300)
# Retorna: https://s3.amazonaws.com/bucket/...?Signature=...
```
