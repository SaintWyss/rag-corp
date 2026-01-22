"""
Name: Timing Utilities

Responsibilities:
  - Provide framework-agnostic timing helpers
  - Measure execution time of code blocks
  - Support both sync and context manager patterns

Collaborators:
  - application/use_cases: Uses Timer for stage measurements
  - metrics.py: Can consume timing data for histograms

Constraints:
  - No framework dependencies (pure Python)
  - Thread/async safe
  - Minimal overhead (<1μs per measurement)

Notes:
  - Use as context manager: with Timer() as t: ... print(t.elapsed_ms)
  - Use as decorator (future): @timed("operation")
"""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Timer:
    """
    R: Simple timer for measuring elapsed time.

    Usage:
        timer = Timer()
        timer.start()
        # ... do work ...
        timer.stop()
        print(f"Took {timer.elapsed_ms}ms")

    Or as context manager:
        with Timer() as t:
            # ... do work ...
        print(f"Took {t.elapsed_ms}ms")
    """

    _start_time: Optional[float] = field(default=None, repr=False)
    _end_time: Optional[float] = field(default=None, repr=False)

    def start(self) -> "Timer":
        """R: Start the timer."""
        self._start_time = time.perf_counter()
        self._end_time = None
        return self

    def stop(self) -> "Timer":
        """R: Stop the timer."""
        if self._start_time is None:
            raise RuntimeError("Timer was not started")
        self._end_time = time.perf_counter()
        return self

    @property
    def elapsed_seconds(self) -> float:
        """R: Get elapsed time in seconds."""
        if self._start_time is None:
            return 0.0
        end = self._end_time or time.perf_counter()
        return end - self._start_time

    @property
    def elapsed_ms(self) -> float:
        """R: Get elapsed time in milliseconds."""
        return round(self.elapsed_seconds * 1000, 2)

    def __enter__(self) -> "Timer":
        """R: Context manager entry - starts timer."""
        return self.start()

    def __exit__(self, *args) -> None:
        """R: Context manager exit - stops timer."""
        self.stop()


@dataclass
class StageTimings:
    """
    R: Container for multi-stage timing measurements.

    Usage:
        timings = StageTimings()

        with timings.measure("embed"):
            embed_result = embed_query(q)

        with timings.measure("retrieve"):
            chunks = search_similar(...)

        print(timings.to_dict())
        # {"embed_ms": 45.2, "retrieve_ms": 12.3, "total_ms": 57.5}
    """

    _stages: dict[str, float] = field(default_factory=dict)
    _total_timer: Timer = field(default_factory=Timer)

    def __post_init__(self):
        """R: Start total timer on creation."""
        self._total_timer.start()

    def measure(self, stage_name: str) -> "_StageTimer":
        """
        R: Create a timer for a named stage.

        Args:
            stage_name: Name of the stage (e.g., "embed", "retrieve", "llm")

        Returns:
            Timer context manager that records to this StageTimings
        """
        return _StageTimer(stage_name, self)

    def record(self, stage_name: str, elapsed_ms: float) -> None:
        """R: Record a stage timing directly."""
        self._stages[stage_name] = elapsed_ms

    def to_dict(self) -> dict[str, float]:
        """
        R: Get all timings as a dict.

        Returns:
            Dict with {stage}_ms keys and total_ms
        """
        result = {f"{name}_ms": ms for name, ms in self._stages.items()}
        result["total_ms"] = self._total_timer.elapsed_ms
        return result


class _StageTimer(Timer):
    """R: Internal timer that records to parent StageTimings."""

    def __init__(self, stage_name: str, parent: StageTimings):
        super().__init__()
        self._stage_name = stage_name
        self._parent = parent

    def __exit__(self, *args) -> None:
        super().__exit__(*args)
        self._parent.record(self._stage_name, self.elapsed_ms)
