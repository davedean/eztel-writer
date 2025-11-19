"""Session state management and lap tracking"""

from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from src.mvp_format import SampleNormalizer


class SessionState(Enum):
    """Session states"""
    IDLE = "idle"
    DETECTED = "detected"
    LOGGING = "logging"
    PAUSED = "paused"
    ERROR = "error"


class SessionManager:
    """
    Manages session state and lap tracking

    Responsibilities:
    - Track session state (idle, logging, etc.)
    - Detect lap changes
    - Buffer telemetry samples for current lap
    - Generate session IDs
    """

    def __init__(
        self,
        normalizer: SampleNormalizer | None = None,
        idle_timeout: float = 5.0,
        min_speed_kmh: float = 1.0,
        lap_reset_tolerance: float = 5.0,
    ):
        self.state = SessionState.IDLE
        self.current_lap = 0
        self.current_session_id = None
        self.lap_samples = []  # Buffer for current lap (normalized samples)
        self.normalizer = normalizer or SampleNormalizer()
        self.idle_timeout = max(0.0, idle_timeout)
        self.min_speed_kmh = max(0.0, min_speed_kmh)
        self.lap_reset_tolerance = max(0.0, lap_reset_tolerance)
        self._last_progress_time: Optional[float] = None
        self.last_lap_distance: Optional[float] = None
        self.lap_start_timestamp: Optional[float] = None
        self.last_lap_time: float = 0.0
        self.track_length: float = 0.0

    def update(
        self, telemetry: Dict[str, Any], timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update session state based on telemetry

        Args:
            telemetry: Current telemetry data
            timestamp: Optional wall-clock timestamp for idle detection

        Returns:
            Dict with events: {'lap_completed': True, 'session_stopped': 'reason', ...}
        """
        events = {}

        # Detect lap change
        new_lap = telemetry.get('lap', 0)
        if new_lap != self.current_lap and self.current_lap > 0:
            events['lap_completed'] = True
            if timestamp is not None:
                self.lap_start_timestamp = timestamp
                self.last_lap_time = 0.0

        self.current_lap = new_lap
        if self.current_lap > 0 and self.lap_start_timestamp is None and timestamp is not None:
            self.lap_start_timestamp = timestamp

        self._update_track_length(telemetry)
        events.update(self._detect_stop_conditions(telemetry, timestamp))

        return events

    def add_sample(self, telemetry: Dict[str, Any], timestamp: Optional[float] = None):
        """
        Add telemetry sample to current lap buffer

        Args:
            telemetry: Telemetry data to buffer
            timestamp: Optional wall-clock timestamp for lap time reconstruction
        """
        if 'track_length' not in telemetry and self.track_length > 0:
            telemetry = {**telemetry, 'track_length': self.track_length}

        normalized = self.normalizer.normalize(telemetry)
        self._assign_lap_time(normalized, timestamp)
        if not self._is_duplicate_sample(normalized):
            self.lap_samples.append(normalized)

    def get_lap_data(self) -> List[Dict[str, Any]]:
        """
        Get all samples for current lap

        Returns:
            List of telemetry samples
        """
        return self.lap_samples.copy()

    def clear_lap_buffer(self):
        """Clear lap buffer after write"""
        self.lap_samples.clear()
        self.last_lap_time = 0.0

    def generate_session_id(self) -> str:
        """
        Generate unique session ID based on timestamp

        Returns:
            Session ID string (timestamp-based)
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return timestamp

    def get_lap_summary(self) -> Dict[str, Any]:
        """
        Calculate lap summary from buffered samples

        Returns:
            Dictionary with lap summary (times, sectors, etc.)
        """
        if not self.lap_samples:
            return {}

        last_sample = self.lap_samples[-1]

        return {
            'lap': self.current_lap,
            'lap_time': last_sample.get('LapTime [s]', 0.0),
            'samples_count': len(self.lap_samples),
            'lap_distance': last_sample.get('LapDistance [m]', 0.0),
        }

    def _detect_stop_conditions(
        self, telemetry: Dict[str, Any], timestamp: Optional[float]
    ) -> Dict[str, str]:
        events: Dict[str, str] = {}
        lap_distance = self._extract_float(
            telemetry, 'lap_distance', 'LapDistance [m]'
        )
        speed = self._extract_float(telemetry, 'speed', 'Speed [km/h]')

        if timestamp is not None and self._last_progress_time is None:
            self._last_progress_time = timestamp

        # Detect abrupt lap distance resets (teleport to pits, session change, etc.)
        if (
            lap_distance is not None
            and self.last_lap_distance is not None
            and lap_distance + self.lap_reset_tolerance < self.last_lap_distance
        ):
            events['session_stopped'] = 'lap_distance_reset'

        # Track forward progress
        if lap_distance is not None:
            if (
                self.last_lap_distance is None
                or lap_distance > self.last_lap_distance + 0.1
            ) and timestamp is not None:
                self._last_progress_time = timestamp
            self.last_lap_distance = lap_distance

        if speed is not None and speed >= self.min_speed_kmh and timestamp is not None:
            self._last_progress_time = timestamp

        # Idle timeout - only if configured (>0)
        if (
            self.idle_timeout > 0
            and timestamp is not None
            and self._last_progress_time is not None
            and (timestamp - self._last_progress_time) >= self.idle_timeout
            and 'session_stopped' not in events
        ):
            events['session_stopped'] = 'idle_timeout'

        if events.get('session_stopped') and timestamp is not None:
            # Reset progress timer so we do not immediately fire again
            self._last_progress_time = timestamp

        return events

    @staticmethod
    def _extract_float(telemetry: Mapping[str, Any], *keys: str) -> Optional[float]:
        for key in keys:
            if key in telemetry and telemetry[key] is not None:
                try:
                    return float(telemetry[key])
                except (TypeError, ValueError):
                    continue
        return None

    def _is_duplicate_sample(self, normalized: Mapping[str, Any]) -> bool:
        if not self.lap_samples:
            return False

        last = self.lap_samples[-1]
        # Treat samples as duplicates only when the fully-normalized payload matches.
        # This keeps truly identical records from being buffered while still allowing
        # repeated distance/time readings that carry new sensor data to be logged.
        return normalized == last

    def _assign_lap_time(
        self, normalized: Dict[str, Any], timestamp: Optional[float]
    ) -> None:
        """Ensure LapTime is present and monotonic using timestamps when available."""

        if timestamp is not None and self.lap_start_timestamp is None:
            self.lap_start_timestamp = timestamp

        reported_time = normalized.get('LapTime [s]')
        reported_time = (
            float(reported_time)
            if reported_time is not None
            else None
        )

        computed_time = None
        if timestamp is not None and self.lap_start_timestamp is not None:
            computed_time = max(0.0, timestamp - self.lap_start_timestamp)

        lap_time = self._select_time_value(reported_time, computed_time)
        normalized['LapTime [s]'] = lap_time
        self.last_lap_time = lap_time

    def _select_time_value(
        self, reported_time: Optional[float], computed_time: Optional[float]
    ) -> float:
        """Pick the best lap time candidate and enforce monotonicity."""

        valid_reported = (
            reported_time
            if reported_time is not None and reported_time >= 0
            else None
        )

        if computed_time is not None:
            if valid_reported is None or valid_reported < computed_time - 0.02:
                chosen = computed_time
            else:
                chosen = max(valid_reported, computed_time)
        else:
            chosen = valid_reported if valid_reported is not None else self.last_lap_time

        if chosen < self.last_lap_time:
            return self.last_lap_time

        return chosen

    def _update_track_length(self, telemetry: Mapping[str, Any]) -> None:
        candidate = self._extract_float(telemetry, 'track_length', 'TrackLen [m]')
        if candidate and candidate > self.track_length:
            self.track_length = candidate

        lap_distance = self._extract_float(
            telemetry, 'lap_distance', 'LapDistance [m]'
        )
        if lap_distance and lap_distance > self.track_length:
            self.track_length = lap_distance
