"""Real telemetry reader from pyRfactor2SharedMemory (Windows only)"""

from typing import Dict, Any, Optional
from datetime import datetime
from .telemetry_interface import TelemetryReaderInterface

# Import REST API client for vehicle metadata
try:
    from ..lmu_rest_api import LMURestAPI
    REST_API_AVAILABLE = True
except ImportError:
    REST_API_AVAILABLE = False
    LMURestAPI = None


class RealTelemetryReader(TelemetryReaderInterface):
    """
    Real telemetry from pyRfactor2SharedMemory

    This module only works on Windows with LMU and the
    rF2SharedMemoryMapPlugin enabled.
    """

    def __init__(self):
        try:
            # Import the shared memory library either from the installed package
            # or the vendored copy (older instructions referenced a local folder).
            from pyRfactor2SharedMemory.sharedMemoryAPI import (
                SimInfoAPI,
                Cbytestring2Python,
            )
        except ImportError:
            import os
            import sys

            local_path = os.path.join(
                os.path.dirname(__file__), "..", "pyRfactor2SharedMemory"
            )
            sys.path.insert(0, local_path)
            try:
                from sharedMemoryAPI import SimInfoAPI, Cbytestring2Python
            except ImportError as e:  # pragma: no cover - Windows-only dependency
                raise ImportError(
                    f"pyRfactor2SharedMemory not found: {e}. "
                    "Install the package (pip install pyRfactor2SharedMemory) "
                    "or add the vendored folder to src/pyRfactor2SharedMemory."
                ) from e

        self.SimInfoAPI = SimInfoAPI
        self.Cbytestring2Python = Cbytestring2Python
        self.info = SimInfoAPI()

        # Initialize REST API client for vehicle metadata
        # Note: We defer the actual data fetch until it's needed (lazy loading)
        # to avoid blocking the app startup. Data will be fetched on first use.
        self.rest_api: Optional[LMURestAPI] = None
        self._rest_api_checked = False  # Track if we've attempted to fetch data
        if REST_API_AVAILABLE and LMURestAPI:
            try:
                self.rest_api = LMURestAPI()
                print("[LMU REST API] Client initialized (data will be fetched when needed)")
            except Exception as e:
                print(f"[LMU REST API] Error initializing: {e}")
                self.rest_api = None

    def is_available(self) -> bool:
        """Check if shared memory is accessible"""
        try:
            return self.info.isSharedMemoryAvailable()
        except Exception:
            return False

    def _try_fetch_vehicle_data(self) -> bool:
        """
        Try to fetch vehicle data from REST API

        Returns:
            True if data was fetched successfully, False otherwise
        """
        if not self.rest_api:
            return False

        try:
            if self.rest_api.is_available():
                data = self.rest_api.fetch_vehicle_data()
                self._rest_api_checked = True
                return len(data) > 0
        except Exception:
            pass

        return False

    def ensure_rest_api_data(self):
        """
        Ensure REST API vehicle data is loaded, retry if not yet fetched

        This method should be called when vehicle metadata is needed.
        It will retry fetching data if the initial attempt failed.
        """
        if not self.rest_api:
            return

        # If we haven't successfully fetched data yet, try again
        if not self._rest_api_checked or not self.rest_api.vehicle_cache:
            if self._try_fetch_vehicle_data():
                print("[LMU REST API] Vehicle metadata loaded on retry")

    def read(self) -> Dict[str, Any]:
        """
        Read from rF2 shared memory and map to our telemetry dict format
        """
        if not self.is_available():
            return {}

        try:
            # Get player's vehicle data
            tele = self.info.playersVehicleTelemetry()
            scor = self.info.playersVehicleScoring()
            scor_info = self.info.Rf2Scor.mScoringInfo

            # Extract track info (prefer telemetry buffer for layout/variant)
            track_name = self.Cbytestring2Python(tele.mTrackName) or self.Cbytestring2Python(
                scor_info.mTrackName
            )
            track_length = float(scor_info.mLapDist)

            # Extract player/car info
            player_name = self.Cbytestring2Python(scor.mDriverName)
            car_name = self.Cbytestring2Python(tele.mVehicleName) or self.Cbytestring2Python(
                scor.mVehicleName
            )

            session_type = self._session_from_int(scor_info.mSession)

            # Get current lap info
            lap = scor.mTotalLaps if scor.mTotalLaps > 0 else 1
            lap_distance = scor.mLapDist  # Lap distance from scoring
            total_distance = scor.mLapDist  # Total distance same as lap distance

            # Infer current sector from sector times
            # sector1_time > 0 means we've completed sector 1 (now in sector 2)
            # sector2_time > 0 means we've completed sector 2 (now in sector 3)
            sector1_time = scor.mCurSector1
            sector2_time = scor.mCurSector2
            if sector2_time > 0.0:
                current_sector = 2  # In sector 3 (0-indexed)
            elif sector1_time > 0.0:
                current_sector = 1  # In sector 2 (0-indexed)
            else:
                current_sector = 0  # In sector 1 (0-indexed)

            # Speed from local velocity magnitude, convert to km/h
            speed = (tele.mLocalVel.x**2 + tele.mLocalVel.y**2 + tele.mLocalVel.z**2)**0.5 * 3.6

            # Return complete telemetry dictionary matching mock format
            return {
                # Player/Session Info
                'player_name': player_name,
                'track_name': track_name,
                'car_name': car_name,
                'session_type': session_type,
                'game_version': '1.0',
                'date': datetime.now(),

                # Lap Info
                'lap': lap,
                'lap_distance': lap_distance,
                'total_distance': total_distance,
                'lap_time': scor.mTimeIntoLap,  # Current lap time (directly from game engine)
                'sector1_time': sector1_time,
                'sector2_time': sector2_time,
                'sector3_time': 0.0,  # Sector 3 calculated from lap - S1 - S2
                'current_sector': current_sector,  # 0-indexed sector (0, 1, or 2)

                # Track Info
                'track_id': 0,  # TODO: Get from game
                'track_length': track_length,
                'track_temp': scor_info.mTrackTemp,
                'ambient_temp': scor_info.mAmbientTemp,
                'weather': 'Clear',  # TODO: Map from weather data
                'wind_speed': 0.0,  # Not available in shared memory
                'wind_direction': 0.0,

                # Car State
                'speed': speed,
                'rpm': tele.mEngineRPM,
                'gear': tele.mGear,
                'throttle': tele.mFilteredThrottle,
                'brake': tele.mFilteredBrake,
                'steering': tele.mFilteredSteering,
                'clutch': tele.mFilteredClutch,
                'drs': 0,  # TODO: Map from telemetry

                # Position
                'position_x': tele.mPos.x,
                'position_y': tele.mPos.y,
                'position_z': tele.mPos.z,
                'yaw': tele.mLocalRot.x,  # Using local rotation as approximation
                'pitch': tele.mLocalRot.y,
                'roll': tele.mLocalRot.z,

                # Physics
                'g_force_lateral': tele.mLocalAccel.x,
                'g_force_longitudinal': tele.mLocalAccel.z,
                'g_force_vertical': tele.mLocalAccel.y,

                # Wheels (RL, RR, FL, FR) - Note: wheel order is FL, FR, RL, RR in rF2
                'wheel_speed': {
                    'rl': abs(tele.mWheels[2].mRotation) * 3.6,  # rad/s to km/h approximation
                    'rr': abs(tele.mWheels[3].mRotation) * 3.6,
                    'fl': abs(tele.mWheels[0].mRotation) * 3.6,
                    'fr': abs(tele.mWheels[1].mRotation) * 3.6,
                },

                # Brake temperatures (FL, FR, RL, RR)
                'brake_temp': {
                    'rl': tele.mWheels[2].mBrakeTemp,
                    'rr': tele.mWheels[3].mBrakeTemp,
                    'fl': tele.mWheels[0].mBrakeTemp,
                    'fr': tele.mWheels[1].mBrakeTemp,
                },

                # Tire temperatures (average across surface) - Convert from Kelvin to Celsius
                'tyre_temp': {
                    'rl': (tele.mWheels[2].mTemperature[0] + tele.mWheels[2].mTemperature[1] + tele.mWheels[2].mTemperature[2]) / 3 - 273.15,
                    'rr': (tele.mWheels[3].mTemperature[0] + tele.mWheels[3].mTemperature[1] + tele.mWheels[3].mTemperature[2]) / 3 - 273.15,
                    'fl': (tele.mWheels[0].mTemperature[0] + tele.mWheels[0].mTemperature[1] + tele.mWheels[0].mTemperature[2]) / 3 - 273.15,
                    'fr': (tele.mWheels[1].mTemperature[0] + tele.mWheels[1].mTemperature[1] + tele.mWheels[1].mTemperature[2]) / 3 - 273.15,
                },

                # Tire surface temperatures - Convert from Kelvin to Celsius
                'tyre_temp_surface': {
                    'rl': {'left': tele.mWheels[2].mTemperature[0] - 273.15, 'center': tele.mWheels[2].mTemperature[1] - 273.15, 'right': tele.mWheels[2].mTemperature[2] - 273.15},
                    'rr': {'left': tele.mWheels[3].mTemperature[0] - 273.15, 'center': tele.mWheels[3].mTemperature[1] - 273.15, 'right': tele.mWheels[3].mTemperature[2] - 273.15},
                    'fl': {'left': tele.mWheels[0].mTemperature[0] - 273.15, 'center': tele.mWheels[0].mTemperature[1] - 273.15, 'right': tele.mWheels[0].mTemperature[2] - 273.15},
                    'fr': {'left': tele.mWheels[1].mTemperature[0] - 273.15, 'center': tele.mWheels[1].mTemperature[1] - 273.15, 'right': tele.mWheels[1].mTemperature[2] - 273.15},
                },

                # Tire wear
                'tyre_wear': {
                    'rl': tele.mWheels[2].mWear,
                    'rr': tele.mWheels[3].mWear,
                    'fl': tele.mWheels[0].mWear,
                    'fr': tele.mWheels[1].mWear,
                },

                # Tire pressure
                'tyre_pressure': {
                    'rl': tele.mWheels[2].mPressure,
                    'rr': tele.mWheels[3].mPressure,
                    'fl': tele.mWheels[0].mPressure,
                    'fr': tele.mWheels[1].mPressure,
                },

                # Suspension position
                'suspension_position': {
                    'rl': tele.mWheels[2].mSuspensionDeflection,
                    'rr': tele.mWheels[3].mSuspensionDeflection,
                    'fl': tele.mWheels[0].mSuspensionDeflection,
                    'fr': tele.mWheels[1].mSuspensionDeflection,
                },

                # Suspension velocity
                'suspension_velocity': {
                    'rl': tele.mWheels[2].mRideHeight,  # Using ride height as proxy
                    'rr': tele.mWheels[3].mRideHeight,
                    'fl': tele.mWheels[0].mRideHeight,
                    'fr': tele.mWheels[1].mRideHeight,
                },

                # Suspension acceleration
                'suspension_acceleration': {
                    'rl': 0.0,  # Not directly available
                    'rr': 0.0,
                    'fl': 0.0,
                    'fr': 0.0,
                },

                # Additional fields
                'engine_temp': tele.mEngineWaterTemp,
                'oil_temp': tele.mEngineOilTemp,
                'oil_pressure': 0.0,  # Not available in shared memory
                'fuel': tele.mFuel,
                'fuel_capacity': tele.mFuelCapacity,
                'drs_available': 0,
                'ers_level': 0.0,
                'kers_level': 0.0,
            }

        except Exception as e:
            # Log error but don't crash
            print(f"Error reading telemetry: {e}")
            return {}

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get session metadata from shared memory
        """
        if not self.is_available():
            return {}

        try:
            scor_info = self.info.Rf2Scor.mScoringInfo
            scor = self.info.playersVehicleScoring()
            tele = self.info.playersVehicleTelemetry()

            return {
                'player_name': self.Cbytestring2Python(scor.mDriverName),
                'track_name': self.Cbytestring2Python(tele.mTrackName)
                or self.Cbytestring2Python(scor_info.mTrackName),
                'car_name': self.Cbytestring2Python(tele.mVehicleName)
                or self.Cbytestring2Python(scor.mVehicleName),
                'session_type': self._session_from_int(scor_info.mSession),
                'game_version': '1.0',
                'date': datetime.now(),
                'track_id': 0,
                'track_length': float(scor_info.mLapDist),
            }
        except Exception as e:
            print(f"Error getting session info: {e}")
            return {}

    def get_all_vehicles(self) -> list[Dict[str, Any]]:
        """
        Get telemetry for all vehicles in session (for opponent tracking)

        Returns:
            List of telemetry dicts, one per vehicle (excludes local player)
            Empty list if not available or not in multiplayer
        """
        if not self.is_available():
            return []

        try:
            scor_info = self.info.Rf2Scor.mScoringInfo
            num_vehicles = scor_info.mNumVehicles

            if num_vehicles <= 1:  # Only player, no opponents
                return []

            vehicles = []

            # Iterate through all vehicles
            for i in range(num_vehicles):
                try:
                    vehicle_scor = self.info.Rf2Scor.mVehicles[i]
                    vehicle_tele = self.info.Rf2Tele.mVehicles[i]

                    # Skip local player (mIsPlayer == True or mControl == 0)
                    if vehicle_scor.mIsPlayer or vehicle_scor.mControl == 0:
                        continue

                    # Extract basic info
                    driver_name = self.Cbytestring2Python(vehicle_scor.mDriverName)
                    if not driver_name:  # Skip empty slots
                        continue

                    car_name = self.Cbytestring2Python(vehicle_tele.mVehicleName) or \
                               self.Cbytestring2Python(vehicle_scor.mVehicleName)

                    # Enrich with REST API data (car model, manufacturer, team name)
                    car_model = ''
                    team_name = ''
                    manufacturer = ''
                    vehicle_class_api = ''

                    if self.rest_api:
                        # Ensure REST API data is loaded (retry if initial fetch failed)
                        self.ensure_rest_api_data()
                        vehicle_meta = self.rest_api.lookup_vehicle(car_name)
                        if vehicle_meta:
                            car_model = vehicle_meta.get('car_model', '')
                            team_name = vehicle_meta.get('team', '')
                            manufacturer = vehicle_meta.get('manufacturer', '')
                            vehicle_class_api = vehicle_meta.get('class', '')

                    # Fallback: if REST API unavailable, use shared memory vehicle class
                    if not vehicle_class_api:
                        vehicle_class_api = self.Cbytestring2Python(vehicle_scor.mVehicleClass) if hasattr(vehicle_scor, 'mVehicleClass') else ''

                    # Get lap info
                    lap = vehicle_scor.mTotalLaps if vehicle_scor.mTotalLaps > 0 else 1
                    lap_distance = vehicle_scor.mLapDist

                    # Get current lap time directly from game engine
                    # Use mTimeIntoLap for current lap in progress
                    lap_time = vehicle_scor.mTimeIntoLap if hasattr(vehicle_scor, 'mTimeIntoLap') else 0.0

                    # Calculate speed from local velocity
                    speed = (vehicle_tele.mLocalVel.x**2 +
                            vehicle_tele.mLocalVel.y**2 +
                            vehicle_tele.mLocalVel.z**2)**0.5 * 3.6  # m/s to km/h

                    # Create telemetry dict for this vehicle
                    vehicle_data = {
                        'driver_name': driver_name,
                        'car_name': car_name,  # Team entry name (e.g., "Action Express Racing #311:LM 1.41")
                        'car_model': car_model,  # Car make/model (e.g., "Cadillac V-Series.R")
                        'team_name': team_name,  # Team name (e.g., "Action Express Racing")
                        'manufacturer': manufacturer,  # Manufacturer (e.g., "Cadillac")
                        'car_class': vehicle_class_api,  # Class (e.g., "Hypercar", "GTE", "GT3")
                        'control': vehicle_scor.mControl,  # -1=nobody, 0=local, 1=AI, 2=remote, 3=replay
                        'position': vehicle_scor.mPlace,
                        'lap': lap,
                        'lap_distance': lap_distance,
                        'lap_time': lap_time,  # mTimeIntoLap (current lap in progress)
                        'last_lap_time': vehicle_scor.mLastLapTime if hasattr(vehicle_scor, 'mLastLapTime') else 0.0,  # Last completed lap
                        'speed': speed,
                        'rpm': vehicle_tele.mEngineRPM,
                        'gear': vehicle_tele.mGear,
                        'throttle': vehicle_tele.mUnfilteredThrottle * 100.0,  # 0-1 to 0-100%
                        'brake': vehicle_tele.mUnfilteredBrake * 100.0,  # 0-1 to 0-100%
                        'steering': vehicle_tele.mUnfilteredSteering * 100.0,  # -1 to 1 to -100% to 100%
                        'position_x': vehicle_tele.mPos.x,
                        'position_y': vehicle_tele.mPos.y,
                        'position_z': vehicle_tele.mPos.z,
                        'track_length': float(scor_info.mLapDist),
                    }

                    vehicles.append(vehicle_data)

                except (AttributeError, IndexError) as e:
                    # Skip vehicle if data unavailable
                    continue

            return vehicles

        except Exception as e:
            print(f"Error getting vehicle data: {e}")
            return []

    @staticmethod
    def _session_from_int(session_code: int) -> str:
        mapping = {
            0: 'TestDay',
            1: 'Practice',
            2: 'Practice',
            3: 'Practice',
            4: 'Practice',
            5: 'Qualifying',
            6: 'Qualifying',
            7: 'Qualifying',
            8: 'Qualifying',
            9: 'Warmup',
            10: 'Race',
            11: 'Race',
            12: 'Race',
            13: 'Race',
        }
        return mapping.get(session_code, 'Practice')
