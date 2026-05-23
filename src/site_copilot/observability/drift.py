"""Lightweight drift detector for the RFI agent.

Watches three signals over a rolling window:
  - response length distribution
  - citation count per response
  - share of responses that escalate to EOR

Any signal moving more than `threshold_std` standard deviations from the
rolling baseline emits a drift event the tracer picks up.

This is a sketch — production would feed these to Databricks ML monitoring or
Bedrock evaluation. The shape matches that contract so the swap is mechanical.
"""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field


@dataclass
class DriftDetector:
    window: int = 50
    threshold_std: float = 3.0
    _lens: deque[float] = field(default_factory=lambda: deque(maxlen=50))
    _cites: deque[float] = field(default_factory=lambda: deque(maxlen=50))
    _eor: deque[float] = field(default_factory=lambda: deque(maxlen=50))

    def observe(self, *, response_len: int, citation_count: int, escalated: bool) -> list[str]:
        alerts: list[str] = []
        for buf, value, name in (
            (self._lens, float(response_len), "response_len"),
            (self._cites, float(citation_count), "citation_count"),
            (self._eor, 1.0 if escalated else 0.0, "escalation_rate"),
        ):
            if len(buf) >= 10:
                mu = statistics.fmean(buf)
                sd = statistics.pstdev(buf) or 1e-6
                if abs(value - mu) > self.threshold_std * sd:
                    alerts.append(
                        f"drift:{name} value={value:.2f} mu={mu:.2f} sd={sd:.2f}"
                    )
            buf.append(value)
        return alerts
