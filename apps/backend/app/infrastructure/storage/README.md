# Infra: File Storage (Blob Store)

## 🎯 Misión

Maneja el almacenamiento de archivos binarios (PDFs, imágenes) subidos por los usuarios.
Abstrae el sistema de archivos o servicio en la nube (S3).

**Qué SÍ hace:**

- Sube, baja y borra archivos.
- Genera URLs presignadas (si el backend lo soporta).

**Qué NO hace:**

- No parsea el contenido.

## 🗺️ Mapa del territorio

| Recurso              | Tipo       | Responsabilidad (en humano)                             |
| :------------------- | :--------- | :------------------------------------------------------ |
| `errors.py`          | 🐍 Archivo | Excepciones específicas de storage (FileNotFound).      |
| `s3_file_storage.py` | 🐍 Archivo | Implementación compatible con S3 (AWS) y MinIO (Local). |

## ⚙️ ¿Cómo funciona por dentro?

Usa `boto3` o librerías similares.
La configuración (Bucket, Region, Endpoint) viene de `crosscutting.config`.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure Adapter.
- **Llama a:** AWS S3 / MinIO Container.

## 👩‍💻 Guía de uso (Snippets)

### Subir archivo

```python
storage = S3FileStorage(bucket="my-bucket", ...)
key = storage.upload(file_bytes, "docs/manual.pdf")
```

## 🧩 Cómo extender sin romper nada

1.  **Local Filesystem:** Podrías crear `LocalFileStorage` para guardar en disco sin usar S3/MinIO para desarrollo ultra-light.

## 🆘 Troubleshooting

- **Síntoma:** "Connection Refused" a MinIO.
  - **Causa:** Docker no está corriendo o el puerto `9000` no está expuesto.

## 🔎 Ver también

- [Ingesta de Documentos (Consumidor)](../../../application/usecases/ingestion/README.md)
