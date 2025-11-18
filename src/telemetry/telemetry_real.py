"""Real telemetry reader from pyRfactor2SharedMemory (Windows only)"""

from typing import Dict, Any
from datetime import datetime
from .telemetry_interface import TelemetryReaderInterface


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

    def is_available(self) -> bool:
        """Check if shared memory is accessible"""
        try:
            return self.info.isSharedMemoryAvailable()
        except Exception:
            return False

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

            # Extract track info
            track_name = self.Cbytestring2Python(scor_info.mTrackName)

            # Extract player/car info
            player_name = self.Cbytestring2Python(scor.mDriverName)
            car_name = self.Cbytestring2Python(scor.mVehicleName)

            # Get current lap info
            lap = scor.mTotalLaps if scor.mTotalLaps > 0 else 1
            lap_distance = scor.mLapDist  # Lap distance from scoring
            total_distance = scor.mLapDist  # Total distance same as lap distance

            # Speed from local velocity magnitude, convert to km/h
            speed = (tele.mLocalVel.x**2 + tele.mLocalVel.y**2 + tele.mLocalVel.z**2)**0.5 * 3.6

            # Return complete telemetry dictionary matching mock format
            return {
                # Player/Session Info
                'player_name': player_name,
                'track_name': track_name,
                'car_name': car_name,
                'session_type': 'Practice',  # TODO: Map from scor_info.mSession
                'game_version': '1.0',
                'date': datetime.now(),

                # Lap Info
                'lap': lap,
                'lap_distance': lap_distance,
                'total_distance': total_distance,
                'lap_time': scor.mLapStartET,
                'sector1_time': scor.mCurSector1,
                'sector2_time': scor.mCurSector2,
                'sector3_time': 0.0,  # Sector 3 calculated from lap - S1 - S2

                # Track Info
                'track_id': 0,  # TODO: Get from game
                'track_length': 0.0,  # TODO: Get from game
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

            return {
                'player_name': self.Cbytestring2Python(scor.mDriverName),
                'track_name': self.Cbytestring2Python(scor_info.mTrackName),
                'car_name': self.Cbytestring2Python(scor.mVehicleName),
                'session_type': 'Practice',  # TODO: Map session type
                'game_version': '1.0',
                'date': datetime.now(),
                'track_id': 0,
                'track_length': 0.0,
            }
        except Exception as e:
            print(f"Error getting session info: {e}")
            return {}
