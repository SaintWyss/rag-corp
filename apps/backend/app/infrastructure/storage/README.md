# Storage (S3/MinIO)

## 🎯 Misión
Implementar el adaptador de almacenamiento de archivos sobre S3 compatible (AWS S3 / MinIO) con errores tipados.

**Qué SÍ hace**
- Sube, descarga y elimina archivos.
- Genera URLs presignadas.
- Tipifica errores de storage.

**Qué NO hace**
- No guarda metadata de documentos (eso está en repositorios).
- No expone endpoints HTTP.

**Analogía (opcional)**
- Es el “depósito de archivos” del backend.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports del adapter y errores. |
| 🐍 `errors.py` | Archivo Python | Errores tipados de storage. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `s3_file_storage.py` | Archivo Python | Adapter S3/MinIO (FileStoragePort). |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: key + bytes/stream desde casos de uso.
- **Proceso**: boto3 maneja la operación contra S3/MinIO.
- **Output**: bytes descargados o confirmación (o error tipado).

Tecnologías/librerías usadas aquí:
- boto3/botocore.

Flujo típico:
- `UploadDocumentUseCase` llama `upload_file()`.
- `DownloadDocumentUseCase` llama `download_file()`.
- Errores de SDK se mapean a `StorageError`.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (storage).
- Recibe órdenes de: Application (use cases).
- Llama a: S3/MinIO vía boto3.
- Contratos y límites: respeta `FileStoragePort` del dominio.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.storage import S3Config, S3FileStorageAdapter

storage = S3FileStorageAdapter(
    S3Config(
        bucket="rag-docs",
        access_key="AKIA...",
        secret_key="SECRET",
        endpoint_url="http://localhost:9000",
    )
)
```

## 🧩 Cómo extender sin romper nada
- Si agregas otro backend, implementa `FileStoragePort` y tipifica errores.
- Mantén lazy import si la dependencia es opcional.
- Agrega tests de integración con MinIO cuando cambies el adapter.

## 🆘 Troubleshooting
- Síntoma: `StorageConfigurationError` → Causa probable: bucket/credenciales faltantes → Mirar `.env`.
- Síntoma: timeouts al subir → Causa probable: endpoint inválido → Revisar `endpoint_url`.
- Síntoma: `StorageNotFoundError` → Causa probable: key inexistente → Revisar `storage_key` en DB.

## 🔎 Ver también
- [Domain services](../../domain/services.py)
- [Ingestion use cases](../../application/usecases/ingestion/README.md)
