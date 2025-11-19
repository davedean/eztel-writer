"""Helpers for the MVP LMU telemetry CSV format."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping


# Canonical telemetry header for the trimmed MVP export
MVP_TELEMETRY_HEADER: List[str] = [
    "LapDistance [m]",
    "LapTime [s]",
    "Sector [int]",
    "Speed [km/h]",
    "EngineRevs [rpm]",
    "ThrottlePercentage [%]",
    "BrakePercentage [%]",
    "Steer [%]",
    "Gear [int]",
    "X [m]",
    "Y [m]",
    "Z [m]",
]


class SampleNormalizer:
    """Normalises raw telemetry dictionaries into the MVP schema."""

    _THREE_DEC_CHANNELS = {"LapDistance [m]", "LapTime [s]"}
    _PERCENT_CHANNELS = {
        "ThrottlePercentage [%]",
        "BrakePercentage [%]",
    }

    def normalize(self, telemetry: Mapping[str, Any]) -> Dict[str, Any]:
        """Return a telemetry sample keyed by the canonical headers."""

        lap_distance = self._to_float(
            telemetry.get("LapDistance [m]"), telemetry.get("lap_distance"), default=0.0
        )
        lap_time = self._to_float(
            telemetry.get("LapTime [s]"), telemetry.get("lap_time"), default=0.0
        )

        sample: Dict[str, Any] = {
            "LapDistance [m]": lap_distance,
            "LapTime [s]": lap_time,
            "Sector [int]": self._resolve_sector(telemetry, lap_distance),
            "Speed [km/h]": self._to_float(
                telemetry.get("Speed [km/h]"), telemetry.get("speed"), default=0.0
            ),
            "EngineRevs [rpm]": self._to_float(
                telemetry.get("EngineRevs [rpm]"),
                telemetry.get("engine_rpm"),
                telemetry.get("rpm"),
                default=0.0,
            ),
            "ThrottlePercentage [%]": self._percent_value(
                telemetry.get("ThrottlePercentage [%]"), telemetry.get("throttle")
            ),
            "BrakePercentage [%]": self._percent_value(
                telemetry.get("BrakePercentage [%]"), telemetry.get("brake")
            ),
            "Steer [%]": self._steering_value(
                telemetry.get("Steer [%]"), telemetry.get("steering")
            ),
            "Gear [int]": self._to_int(
                telemetry.get("Gear [int]"), telemetry.get("gear"), default=0
            ),
            "X [m]": self._optional_float(
                telemetry.get("X [m]"), telemetry.get("position_x")
            ),
            "Y [m]": self._optional_float(
                telemetry.get("Y [m]"), telemetry.get("position_y")
            ),
            "Z [m]": self._optional_float(
                telemetry.get("Z [m]"), telemetry.get("position_z")
            ),
        }

        return sample

    def _to_float(self, *values: Any, default: float = 0.0) -> float:
        for value in values:
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return float(default)

    def _optional_float(self, *values: Any) -> Any:
        for value in values:
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    def _to_int(self, *values: Any, default: int = 0) -> int:
        for value in values:
            if value is None:
                continue
            try:
                return int(round(float(value)))
            except (TypeError, ValueError):
                continue
        return int(default)

    def _percent_value(self, *values: Any) -> float:
        for value in values:
            if value is None:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue

            # Values <= 1.0 are assumed to be fractional (0–1) inputs.
            if -1.5 <= number <= 1.5:
                number *= 100.0

            return max(0.0, min(100.0, number))

        return 0.0

    def _steering_value(self, *values: Any) -> float:
        for value in values:
            if value is None:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue

            # Steering from LMU is typically -1..1 radians/ratio.
            if -2.0 <= number <= 2.0:
                number *= 100.0

            return max(-100.0, min(100.0, number))

        return 0.0

    def _resolve_sector(self, telemetry: Mapping[str, Any], lap_distance: float) -> int:
        for key in ("Sector [int]", "sector", "sector_index", "current_sector"):
            if key in telemetry and telemetry[key] is not None:
                try:
                    sector = int(telemetry[key])
                except (TypeError, ValueError):
                    break
                if sector > 0:
                    sector -= 1
                return max(0, sector)

        track_length = self._to_float(
            telemetry.get("TrackLen [m]"), telemetry.get("track_length"), default=0.0
        )
        if track_length > 0.0:
            progress = max(0.0, min(0.9999, lap_distance / track_length))
            return int(progress * 3)

        return 0


def build_metadata_block(
    session_info: Mapping[str, Any],
    lap_samples: Iterable[Mapping[str, Any]],
) -> "OrderedDict[str, str]":
    """Assemble ordered metadata rows for the MVP CSV preamble."""

    metadata = OrderedDict()
    metadata["Format"] = "LMUTelemetry v2"
    metadata["Version"] = "1"
    metadata["Player"] = _first_value(
        session_info, "player_name", "Player", fallback="Unknown Driver"
    )
    metadata["TrackName"] = _first_value(
        session_info, "track_name", "TrackName", fallback="Unknown Track"
    )
    metadata["CarName"] = _first_value(
        session_info, "car_name", "CarName", fallback="Unknown Car"
    )
    metadata["SessionUTC"] = _resolve_session_time(session_info)
    metadata["LapTime [s]"] = _format_decimal(_max_sample_value(lap_samples, "LapTime [s]"), 3)

    track_length = _first_float(
        session_info.get("TrackLen [m]"),
        session_info.get("track_length"),
        _max_sample_value(lap_samples, "LapDistance [m]"),
        default=0.0,
        require_positive=True,
    )
    metadata["TrackLen [m]"] = _format_decimal(track_length, 2)

    # Optional metadata derived from session info
    optional_pairs = OrderedDict(
        [
            ("GameVersion", session_info.get("game_version")),
            ("Event", session_info.get("session_type")),
            ("TyreCompound", session_info.get("tyre_compound")),
            ("Weather", session_info.get("weather")),
            ("FuelAtStart", session_info.get("fuel_at_start")),
        ]
    )

    for key, value in optional_pairs.items():
        if value is None:
            continue
        if isinstance(value, (int, float)):
            metadata[key] = _format_decimal(float(value), 2)
        else:
            metadata[key] = str(value)

    extras = session_info.get("metadata_extras")
    if isinstance(extras, Mapping):
        for key, value in extras.items():
            metadata[key] = str(value)

    return metadata


def _first_value(
    mapping: Mapping[str, Any],
    *keys: str,
    fallback: str = "",
) -> str:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return str(mapping[key])
    return fallback


def _resolve_session_time(session_info: Mapping[str, Any]) -> str:
    for key in ("session_utc", "SessionUTC", "date"):
        value = session_info.get(key)
        if value is None:
            continue
        if isinstance(value, datetime):
            dt = value
        else:
            try:
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                return str(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _max_sample_value(
    samples: Iterable[Mapping[str, Any]],
    key: str,
) -> float:
    maximum = 0.0
    for sample in samples:
        try:
            value = float(sample.get(key, 0.0))
        except (TypeError, ValueError):
            continue
        if value > maximum:
            maximum = value
    return maximum


def _format_decimal(value: float, min_decimals: int) -> str:
    formatted = f"{value:.6f}".rstrip("0").rstrip(".")
    if "." in formatted:
        decimals = len(formatted.split(".")[1])
    else:
        decimals = 0

    if decimals < min_decimals:
        if "." not in formatted:
            formatted += "."
            decimals = 0
        formatted += "0" * (min_decimals - decimals)

    return formatted


def _first_float(*values: Any, default: float = 0.0, require_positive: bool = False) -> float:
    for value in values:
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue

        if require_positive and numeric <= 0:
            continue

        return numeric
    return float(default)
