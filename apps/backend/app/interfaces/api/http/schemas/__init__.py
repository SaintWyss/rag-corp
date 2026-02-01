"""
===============================================================================
TARJETA CRC — schemas/__init__.py
===============================================================================

Módulo:
    Paquete de Schemas HTTP (DTOs Pydantic)

Responsabilidades:
    - Agrupar contratos HTTP por bounded context (documents/query/workspaces/admin).
    - Mantener separados DTOs (schemas) de controladores (routers).
    - Evitar imports circulares (cada archivo solo importa lo necesario).

Reglas:
    - Schemas NO deben importar infraestructura.
    - Schemas NO deben ejecutar casos de uso.
    - Solo tipos y validación de input/output.
===============================================================================
"""

__all__ = []
