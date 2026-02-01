# apps/backend/app/crosscutting/timing.py
"""
===============================================================================
MÓDULO: Timing utilities (Timer + StageTimings)
===============================================================================

Objetivo
--------
Medición precisa y simple de tiempos:
- Timer (context manager)
- StageTimings (múltiples etapas: embed/retrieve/llm)

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componentes:
  - Timer
  - StageTimings

Responsabilidades:
  - Medir elapsed time sin dependencias externas
  - Exponer resultados en ms para logs/métricas
===============================================================================
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Timer:
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      Timer

    Responsabilidades:
      - Medir elapsed time con perf_counter
      - Soportar uso manual y como context manager

    Colaboradores:
      - StageTimings
    ----------------------------------------------------------------------------
    """

    _start_time: Optional[float] = field(default=None, repr=False)
    _end_time: Optional[float] = field(default=None, repr=False)

    def start(self) -> "Timer":
        self._start_time = time.perf_counter()
        self._end_time = None
        return self

    def stop(self) -> "Timer":
        if self._start_time is None:
            raise RuntimeError("Timer no iniciado")
        self._end_time = time.perf_counter()
        return self

    @property
    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        end = self._end_time or time.perf_counter()
        return end - self._start_time

    @property
    def elapsed_ms(self) -> float:
        return round(self.elapsed_seconds * 1000, 2)

    def __enter__(self) -> "Timer":
        return self.start()

    def __exit__(self, *args) -> None:
        self.stop()


@dataclass
class StageTimings:
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      StageTimings

    Responsabilidades:
      - Medir tiempos por etapa
      - Exponer diccionario con {stage}_ms y total_ms

    Colaboradores:
      - Use cases (RAG pipeline)
    ----------------------------------------------------------------------------
    """

    _stages: dict[str, float] = field(default_factory=dict)
    _total_timer: Timer = field(default_factory=Timer)

    def __post_init__(self) -> None:
        self._total_timer.start()

    def measure(self, stage_name: str) -> "_StageTimer":
        return _StageTimer(stage_name, self)

    def record(self, stage_name: str, elapsed_ms: float) -> None:
        self._stages[stage_name] = elapsed_ms

    def to_dict(self) -> dict[str, float]:
        result = {f"{k}_ms": v for k, v in self._stages.items()}
        result["total_ms"] = self._total_timer.elapsed_ms
        return result


class _StageTimer(Timer):
    def __init__(self, stage_name: str, parent: StageTimings):
        super().__init__()
        self._stage_name = stage_name
        self._parent = parent

    def __exit__(self, *args) -> None:
        super().__exit__(*args)
        self._parent.record(self._stage_name, self.elapsed_ms)
