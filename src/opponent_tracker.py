"""Opponent lap tracking for multiplayer sessions"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OpponentLapData:
    """Data for a completed opponent lap"""
    driver_name: str
    lap_number: int
    lap_time: float
    samples: List[Dict[str, Any]]
    is_fastest: bool
    position: Optional[int] = None
    car_name: Optional[str] = None  # Team entry name (e.g., "Action Express Racing #311:LM")
    car_model: Optional[str] = None  # Car make/model (e.g., "Cadillac V-Series.R")
    team_name: Optional[str] = None  # Team name (e.g., "Action Express Racing")
    manufacturer: Optional[str] = None  # Manufacturer (e.g., "Cadillac")
    car_class: Optional[str] = None  # Vehicle class (e.g., "Hypercar", "GTE", "GT3")


class OpponentTracker:
    """
    Tracks opponent laps during multiplayer sessions

    Implements "fastest lap only" strategy: only returns completed laps
    that are faster than the opponent's previous fastest lap.

    Responsibilities:
    - Track lap data for each opponent (keyed by driver name)
    - Detect lap completion (lap number change)
    - Compare lap times and return only fastest laps
    - Filter by control type (remote players, AI, etc.)
    """

    def __init__(self, track_remote_only: bool = True, track_ai: bool = False):
        """
        Initialize opponent tracker

        Args:
            track_remote_only: If True, only track remote players (default)
            track_ai: If True, also track AI opponents (default: False)
        """
        self.opponents: Dict[str, Dict[str, Any]] = {}
        self.track_remote_only = track_remote_only
        self.track_ai = track_ai

    def update_opponent(
        self,
        telemetry: Dict[str, Any],
        timestamp: Optional[float] = None
    ) -> List[OpponentLapData]:
        """
        Update opponent telemetry and detect lap completions

        Args:
            telemetry: Telemetry data for one opponent
            timestamp: Optional wall-clock timestamp

        Returns:
            List of OpponentLapData for completed laps that should be saved
            (only returns laps that are faster than previous fastest)
        """
        driver_name = telemetry.get('driver_name')
        if not driver_name:
            return []

        control = telemetry.get('control', -1)
        if not self._should_track(control):
            return []

        # Initialize opponent tracking if first time seeing them
        if driver_name not in self.opponents:
            self.opponents[driver_name] = {
                'current_lap': 0,
                'samples': [],
                'fastest_lap_time': float('inf'),
                'lap_start_timestamp': timestamp,
            }

        opponent = self.opponents[driver_name]
        current_lap = telemetry.get('lap', 0)
        completed_laps = []

        # Detect lap completion (lap number increased)
        if current_lap > opponent['current_lap'] and opponent['current_lap'] > 0:
            # Get last completed lap time from shared memory
            # Use 'last_lap_time' (mLastLapTime) not 'lap_time' (mTimeIntoLap)
            # When lap changes 3→4, lap_time=0.5s (time into new lap 4)
            # but last_lap_time=95.2s (completed lap 3 time)
            lap_time = telemetry.get('last_lap_time', 0.0)

            # Skip if last lap time is invalid (first lap, out-lap, etc.)
            if lap_time <= 0.0:
                # Clear samples for new lap and continue tracking
                opponent['samples'] = []
                opponent['lap_start_timestamp'] = timestamp
                opponent['current_lap'] = current_lap
                return []

            # Check if this lap is faster than previous fastest
            is_fastest = lap_time < opponent['fastest_lap_time']

            if is_fastest:
                # Update fastest lap time
                opponent['fastest_lap_time'] = lap_time

            # Create lap data (we return all first laps, then only faster laps)
            if opponent['fastest_lap_time'] == float('inf') or is_fastest:
                lap_data = OpponentLapData(
                    driver_name=driver_name,
                    lap_number=opponent['current_lap'],
                    lap_time=lap_time,
                    samples=opponent['samples'].copy(),
                    is_fastest=True,  # Mark as fastest since we only return fastest
                    position=telemetry.get('position'),
                    car_name=telemetry.get('car_name'),
                    car_model=telemetry.get('car_model'),
                    team_name=telemetry.get('team_name'),
                    manufacturer=telemetry.get('manufacturer'),
                    car_class=telemetry.get('car_class'),
                )
                completed_laps.append(lap_data)

            # Clear samples for new lap
            opponent['samples'] = []
            opponent['lap_start_timestamp'] = timestamp

        # Update current lap
        opponent['current_lap'] = current_lap

        # Add sample to buffer
        if current_lap > 0:
            opponent['samples'].append(telemetry.copy())

        return completed_laps

    def _should_track(self, control: int) -> bool:
        """
        Determine if vehicle should be tracked based on control type

        Args:
            control: Control type from shared memory
                -1 = nobody
                0 = local player
                1 = AI
                2 = remote player
                3 = replay

        Returns:
            True if vehicle should be tracked
        """
        # Never track local player (0), nobody (-1), or replay (3)
        if control in [-1, 0, 3]:
            return False

        # Remote players (2)
        if control == 2:
            return True

        # AI (1) - only if enabled
        if control == 1:
            return self.track_ai

        return False

    def get_opponent_count(self) -> int:
        """
        Get number of opponents currently being tracked

        Returns:
            Count of opponents
        """
        return len(self.opponents)

    def get_opponent_status(self, driver_name: str) -> Optional[Dict[str, Any]]:
        """
        Get current status for an opponent

        Args:
            driver_name: Driver name

        Returns:
            Status dict or None if not tracked
        """
        return self.opponents.get(driver_name)

    def reset(self):
        """Clear all opponent tracking data"""
        self.opponents.clear()
