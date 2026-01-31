"""
===============================================================================
WORKSPACE USE CASE RESULTS (Shared Result / Error Models)
===============================================================================

Name:
    Workspace Use Case Results

Business Goal:
    Proveer modelos compartidos de resultados y errores para los casos de uso
    de Workspaces, con un contrato estable y explícito para:
      - validaciones
      - autorización
      - recursos no encontrados
      - conflictos de negocio

Why (Context / Intención):
    - Los use cases devuelven resultados tipados en lugar de lanzar excepciones
      “hacia afuera”, facilitando:
        * integración con API/HTTP (mapeo a status codes)
        * tests unitarios de flujos
        * consistencia entre casos de uso
    - Unificar errores reduce duplicación y evita mensajes/códigos inconsistentes.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Component:
    workspace_results models (module)

Responsibilities:
    - Definir un conjunto acotado de WorkspaceErrorCode para el dominio
      de Workspaces.
    - Representar WorkspaceError (code + message) como contrato de error.
    - Representar resultados:
        * WorkspaceResult (single workspace)
        * WorkspaceListResult (list of workspaces)
        * ArchiveWorkspaceResult (command specific: archived flag)

Collaborators:
    - domain.entities.Workspace (tipo de entidad retornada)
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from ....domain.entities import Workspace


class WorkspaceErrorCode(str, Enum):
    """
    Enumeración de códigos de error para casos de uso de Workspaces.

    Notas de diseño:
      - str + Enum facilita serialización directa (por ejemplo, en JSON).
      - Los códigos representan categorías estables (no mensajes).
      - Mantener un set pequeño y consistente evita “explosión” de variantes.

    Códigos:
      - VALIDATION_ERROR: inputs inválidos o incompletos.
      - FORBIDDEN: actor no autorizado para la operación.
      - NOT_FOUND: workspace inexistente o no accesible como activo.
      - CONFLICT: colisión de unicidad o regla de negocio (ej. nombre duplicado).
    """

    VALIDATION_ERROR = "VALIDATION_ERROR"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class WorkspaceError:
    """
    Error de caso de uso.

    Campos:
      - code: categoría estable (WorkspaceErrorCode)
      - message: descripción humana, útil para UI/logs

    Nota:
      - Se mantiene simple: sin stack traces, sin metadata de infraestructura.
      - Si en el futuro necesitás i18n o machine-readable details, se puede
        extender con un 'details' dict sin romper compatibilidad.
    """

    code: WorkspaceErrorCode
    message: str


@dataclass
class WorkspaceResult:
    """
    Resultado para casos de uso que retornan un único Workspace.

    Contrato:
      - Si error is None => workspace debe estar presente (éxito)
      - Si error != None => workspace debería ser None (fallo)

    Nota:
      - No se impone estrictamente a nivel runtime, pero se recomienda mantener
        esta convención para consistencia.
    """

    workspace: Workspace | None = None
    error: WorkspaceError | None = None


@dataclass
class WorkspaceListResult:
    """
    Resultado para casos de uso que retornan múltiples Workspaces.

    Contrato:
      - workspaces: lista (posiblemente vacía) en éxito
      - error: presente cuando falla la operación (por ejemplo, actor inválido)

    Nota:
      - Siempre devolvemos lista para simplificar consumo en UI/API.
    """

    workspaces: List[Workspace]
    error: WorkspaceError | None = None


@dataclass
class ArchiveWorkspaceResult:
    """
    Resultado específico para el comando Archive Workspace.

    Campos:
      - archived: True si el workspace quedó archivado (o ya lo estaba)
      - error: presente si la operación no pudo realizarse

    Nota:
      - Este resultado existe porque el comando "archive" puede ser idempotente
        y no necesariamente requiere devolver la entidad completa.
    """

    archived: bool
    error: WorkspaceError | None = None
