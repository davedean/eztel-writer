"""CSV formatter for the MVP telemetry specification."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any, Dict, Iterable, List, Mapping

from src.mvp_format import MVP_TELEMETRY_HEADER


class CSVFormatter:
    """Render normalized telemetry samples into the MVP CSV layout."""

    def __init__(self, header: Iterable[str] | None = None):
        self.header = list(header or MVP_TELEMETRY_HEADER)
        self._int_columns = {col for col in self.header if col.endswith("[int]")}
        self._three_decimal_columns = {"LapDistance [m]", "LapTime [s]"}
        self._two_decimal_columns = {
            "Speed [km/h]",
            "EngineRevs [rpm]",
            "ThrottlePercentage [%]",
            "BrakePercentage [%]",
            "Steer [%]",
            "X [m]",
            "Y [m]",
            "Z [m]",
        }

        # Required metadata order for the preamble
        self.metadata_order = [
            "Format",
            "Version",
            "Player",
            "TrackName",
            "CarModel",  # Car make/model (e.g., "Cadillac V-Series.R")
            "CarClass",  # Vehicle class (e.g., "Hypercar", "GTE", "GT3")
            "Manufacturer",  # Manufacturer (e.g., "Cadillac")
            "TeamName",  # Team name (e.g., "Action Express Racing")
            "CarName",  # Team entry name (legacy, for backward compatibility)
            "SessionUTC",
            "LapTime [s]",
            "TrackLen [m]",
        ]

    def format_lap(
        self,
        lap_data: List[Mapping[str, Any]],
        metadata: Mapping[str, Any],
    ) -> str:
        """Format normalized lap samples + metadata into CSV text."""

        if not lap_data:
            return ""

        lines: List[str] = []

        # Metadata preamble
        for key in self.metadata_order:
            if key in metadata:
                lines.append(f"{key},{metadata[key]}")

        for key, value in metadata.items():
            if key in self.metadata_order:
                continue
            lines.append(f"{key},{value}")

        lines.append("")  # Blank line between metadata and telemetry
        lines.append(",".join(self.header))

        for sample in sorted(lap_data, key=lambda item: item.get("LapDistance [m]", 0.0)):
            lines.append(self._format_sample_row(sample))

        return "\n".join(lines) + "\n"

    def _format_sample_row(self, sample: Mapping[str, Any]) -> str:
        values = []
        for column in self.header:
            value = sample.get(column)
            if value is None or value == "":
                values.append("")
                continue

            if column in self._int_columns:
                try:
                    values.append(str(int(round(float(value)))))
                except (TypeError, ValueError):
                    values.append("0")
                continue

            if column in self._three_decimal_columns:
                values.append(self._format_decimal(value, 3))
                continue

            if column in self._two_decimal_columns:
                values.append(self._format_decimal(value, 2))
                continue

            values.append(str(value))

        return ",".join(values)

    def _format_decimal(self, value: Any, decimals: int) -> str:
        quantize_target = Decimal("1" if decimals == 0 else "1." + ("0" * decimals))

        try:
            numeric = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            numeric = Decimal(0)

        quantized = numeric.quantize(quantize_target, rounding=ROUND_HALF_UP)
        return f"{quantized:.{decimals}f}"
