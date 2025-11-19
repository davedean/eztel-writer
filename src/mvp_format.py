"""Helpers for the MVP LMU telemetry CSV format."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Tuple


# Canonical telemetry header for the trimmed MVP export
# LMUTelemetry v3: Removed LapTime (redundant with metadata) and Y (elevation not needed)
MVP_TELEMETRY_HEADER: List[str] = [
    "LapDistance [m]",
    "Sector [int]",
    "Speed [km/h]",
    "EngineRevs [rpm]",
    "ThrottlePercentage [%]",
    "BrakePercentage [%]",
    "Steer [%]",
    "Gear [int]",
    "X [m]",
    "Z [m]",
]


class SampleNormalizer:
    """Normalises raw telemetry dictionaries into the MVP schema."""

    _THREE_DEC_CHANNELS = {"LapDistance [m]"}
    _PERCENT_CHANNELS = {
        "ThrottlePercentage [%]",
        "BrakePercentage [%]",
    }

    def normalize(self, telemetry: Mapping[str, Any]) -> Dict[str, Any]:
        """Return a telemetry sample keyed by the canonical headers."""

        lap_distance = self._to_float(
            telemetry.get("LapDistance [m]"), telemetry.get("lap_distance"), default=0.0
        )

        sample: Dict[str, Any] = {
            "LapDistance [m]": lap_distance,
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
        # Check for explicit sector index in telemetry
        for key in ("Sector [int]", "sector", "sector_index", "current_sector"):
            if key in telemetry and telemetry[key] is not None:
                try:
                    sector = int(telemetry[key])
                except (TypeError, ValueError):
                    break
                if sector > 0:
                    sector -= 1
                return max(0, sector)

        # Use sector boundaries if available
        sector_boundaries = telemetry.get("sector_boundaries")
        if sector_boundaries and isinstance(sector_boundaries, (list, tuple)):
            for i, boundary in enumerate(sector_boundaries):
                if lap_distance < boundary:
                    return i
            # If beyond all boundaries, return last sector
            return len(sector_boundaries) - 1

        # Fall back to equal division based on track length
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
    metadata["Format"] = "LMUTelemetry v3"
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

    # Add sector boundary information
    sector_boundaries = session_info.get("sector_boundaries")
    if sector_boundaries and isinstance(sector_boundaries, (list, tuple)) and len(sector_boundaries) > 0:
        metadata["NumSectors"] = str(len(sector_boundaries))
        for i, boundary in enumerate(sector_boundaries, start=1):
            metadata[f"Sector{i}End [m]"] = _format_decimal(float(boundary), 2)

    sector_times = _resolve_sector_times(session_info, lap_samples, metadata["LapTime [s]"])
    for index, sector_time in enumerate(sector_times, start=1):
        if sector_time is None:
            continue
        metadata[f"Sector{index}Time [s]"] = _format_decimal(sector_time, 3)

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


def _resolve_sector_times(
    session_info: Mapping[str, Any],
    lap_samples: Iterable[Mapping[str, Any]],
    lap_time: str,
) -> List[float | None]:
    """Determine sector split times from session info or lap samples."""

    def _positive(value: Any) -> float | None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric if numeric > 0 else None

    # Prefer explicit sector info from the session source.
    s1 = _positive(session_info.get("sector1_time"))
    s2 = _positive(session_info.get("sector2_time"))
    s3 = _positive(session_info.get("sector3_time"))

    if s1 and s2 and s3:
        return [s1, s2, s3]

    derived = _derive_sector_splits(lap_samples)
    if derived:
        s1 = s1 or derived.get(0)
        s2 = s2 or derived.get(1)
        s3 = s3 or derived.get(2)

    try:
        lap_total = float(lap_time)
    except (TypeError, ValueError):
        lap_total = None

    if lap_total is not None and (s1 or s2) and s3 is None:
        remainder = lap_total - (s1 or 0.0) - (s2 or 0.0)
        if remainder > 0:
            s3 = remainder

    return [s1, s2, s3]


def _derive_sector_splits(
    lap_samples: Iterable[Mapping[str, Any]]
) -> Dict[int, float]:
    splits: Dict[int, float] = {}
    for sample in sorted(
        lap_samples, key=lambda s: s.get("LapDistance [m]", 0.0)
    ):
        try:
            sector = int(sample.get("Sector [int]", 0))
            lap_time = float(sample.get("LapTime [s]", 0.0))
        except (TypeError, ValueError):
            continue

        if sector <= 0:
            continue

        if sector not in splits and lap_time > 0:
            splits[sector - 1] = lap_time
            if len(splits) >= 2:
                break

    return splits


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


def detect_sector_boundaries(
    telemetry_samples: Iterable[Mapping[str, Any]],
    track_length: float,
) -> Tuple[List[float], int]:
    """
    Detect sector boundaries from telemetry samples.

    Args:
        telemetry_samples: Telemetry samples from a lap
        track_length: Total track length in meters

    Returns:
        Tuple of (boundaries, num_sectors) where boundaries is a list of lap distances
        where each sector ends, and num_sectors is the total number of sectors.
    """
    # Sort samples by lap distance
    sorted_samples = sorted(telemetry_samples, key=lambda s: s.get('lap_distance', 0.0))

    # Track when sector times transition from 0 to positive
    boundaries = []
    prev_sector1 = 0.0
    prev_sector2 = 0.0
    prev_sector3 = 0.0

    for sample in sorted_samples:
        sector1_time = sample.get('sector1_time', 0.0) or 0.0
        sector2_time = sample.get('sector2_time', 0.0) or 0.0
        sector3_time = sample.get('sector3_time', 0.0) or 0.0
        lap_distance = sample.get('lap_distance', 0.0) or 0.0

        # Detect sector 1 completion (transition from 0 to positive)
        if prev_sector1 == 0.0 and sector1_time > 0.0:
            boundaries.append(lap_distance)

        # Detect sector 2 completion
        elif prev_sector2 == 0.0 and sector2_time > 0.0:
            boundaries.append(lap_distance)

        # Detect sector 3 completion
        elif prev_sector3 == 0.0 and sector3_time > 0.0:
            boundaries.append(lap_distance)

        prev_sector1 = sector1_time
        prev_sector2 = sector2_time
        prev_sector3 = sector3_time

    # If no boundaries detected, fall back to equal division (3 sectors)
    if not boundaries and track_length > 0:
        boundaries = [track_length / 3, track_length * 2 / 3, track_length]
        num_sectors = 3
    else:
        # Always include track_length as final boundary
        if track_length > 0:
            if not boundaries or boundaries[-1] < track_length * 0.95:
                boundaries.append(track_length)
        # Determine number of sectors
        num_sectors = len(boundaries) if boundaries else 3

    return boundaries, num_sectors


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
