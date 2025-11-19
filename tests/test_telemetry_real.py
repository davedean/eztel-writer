"""Tests for RealTelemetryReader"""

import pytest
import sys
from unittest.mock import MagicMock, Mock


class TestRealTelemetryReader:
    """Test RealTelemetryReader lap time calculation"""

    @pytest.fixture
    def mock_rf2_module(self):
        """Mock the pyRfactor2SharedMemory module"""
        # Create a mock module
        mock_module = Mock()

        # Mock the classes we need
        mock_sim_api = Mock()
        mock_cbytestring = Mock(side_effect=lambda x: x.decode('utf-8') if isinstance(x, bytes) else str(x))

        mock_module.sharedMemoryAPI.SimInfoAPI = mock_sim_api
        mock_module.sharedMemoryAPI.Cbytestring2Python = mock_cbytestring

        # Inject into sys.modules
        sys.modules['pyRfactor2SharedMemory'] = mock_module
        sys.modules['pyRfactor2SharedMemory.sharedMemoryAPI'] = mock_module.sharedMemoryAPI

        yield mock_sim_api, mock_cbytestring

        # Cleanup
        if 'pyRfactor2SharedMemory' in sys.modules:
            del sys.modules['pyRfactor2SharedMemory']
        if 'pyRfactor2SharedMemory.sharedMemoryAPI' in sys.modules:
            del sys.modules['pyRfactor2SharedMemory.sharedMemoryAPI']

    def test_lap_time_calculated_correctly(self, mock_rf2_module):
        """Test that lap_time is read from mTimeIntoLap"""
        mock_sim_api_class, mock_cbytestring = mock_rf2_module

        # Create mock API instance
        mock_api = MagicMock()
        mock_sim_api_class.return_value = mock_api

        # Mock telemetry data
        mock_tele = MagicMock()
        mock_tele.mTrackName = b'Sebring International Raceway'
        mock_tele.mVehicleName = b'BMW M4 GT3'
        mock_tele.mLocalVel.x = 50.0
        mock_tele.mLocalVel.y = 0.0
        mock_tele.mLocalVel.z = 10.0
        mock_tele.mEngineRPM = 5000.0
        mock_tele.mGear = 4
        mock_tele.mFilteredThrottle = 0.8
        mock_tele.mFilteredBrake = 0.0
        mock_tele.mFilteredSteering = 0.1
        mock_tele.mFilteredClutch = 0.0
        mock_tele.mPos.x = 100.0
        mock_tele.mPos.y = 10.0
        mock_tele.mPos.z = 200.0
        mock_tele.mLocalRot.x = 0.0
        mock_tele.mLocalRot.y = 0.0
        mock_tele.mLocalRot.z = 0.0
        mock_tele.mLocalAccel.x = 0.0
        mock_tele.mLocalAccel.y = 0.0
        mock_tele.mLocalAccel.z = 0.0

        mock_wheel = MagicMock()
        mock_wheel.mRotation = 10.0
        mock_wheel.mBrakeTemp = 300.0
        mock_wheel.mTemperature = [350.0, 350.0, 350.0]
        mock_tele.mWheels = [mock_wheel] * 4

        # Mock scoring data
        mock_scor = MagicMock()
        mock_scor.mDriverName = b'David Dean'
        mock_scor.mVehicleName = b'BMW M4 GT3'
        mock_scor.mTotalLaps = 5
        mock_scor.mLapDist = 1500.0

        # Use mTimeIntoLap directly (fixed in v0.2.1)
        # Simulates a lap that's 130 seconds in progress
        mock_scor.mTimeIntoLap = 130.0
        mock_scor.mCurSector1 = 45.0
        mock_scor.mCurSector2 = 42.0

        # Mock scoring info
        mock_scor_info = MagicMock()
        mock_scor_info.mTrackName = b'Sebring'
        mock_scor_info.mLapDist = 5954.0
        mock_scor_info.mTrackTemp = 35.0
        mock_scor_info.mAmbientTemp = 25.0
        mock_scor_info.mSession = 5

        mock_api.playersVehicleTelemetry.return_value = mock_tele
        mock_api.playersVehicleScoring.return_value = mock_scor
        mock_api.Rf2Scor.mScoringInfo = mock_scor_info
        mock_api.isSharedMemoryAvailable.return_value = True

        # Now import and test
        from src.telemetry.telemetry_real import RealTelemetryReader

        reader = RealTelemetryReader()
        data = reader.read()

        # Verify lap_time is read from mTimeIntoLap
        assert 'lap_time' in data, "lap_time should be present in telemetry data"
        assert data['lap_time'] == pytest.approx(130.0, abs=0.1), \
            f"Expected lap_time=130.0s (2:10), got {data['lap_time']}s"

    def test_lap_time_at_lap_start(self, mock_rf2_module):
        """Test lap_time when at the start of a lap"""
        mock_sim_api_class, mock_cbytestring = mock_rf2_module

        mock_api = MagicMock()
        mock_sim_api_class.return_value = mock_api

        # Simplified mocks
        mock_tele = MagicMock()
        mock_tele.mTrackName = b'Sebring'
        mock_tele.mVehicleName = b'BMW M4 GT3'
        mock_tele.mLocalVel.x = mock_tele.mLocalVel.y = mock_tele.mLocalVel.z = 0.0
        mock_tele.mEngineRPM = 2000.0
        mock_tele.mGear = 1
        mock_tele.mFilteredThrottle = mock_tele.mFilteredBrake = 0.0
        mock_tele.mFilteredSteering = mock_tele.mFilteredClutch = 0.0
        mock_tele.mPos.x = mock_tele.mPos.y = mock_tele.mPos.z = 0.0
        mock_tele.mLocalRot.x = mock_tele.mLocalRot.y = mock_tele.mLocalRot.z = 0.0
        mock_tele.mLocalAccel.x = mock_tele.mLocalAccel.y = mock_tele.mLocalAccel.z = 0.0
        mock_wheel = MagicMock()
        mock_wheel.mRotation = 0.0
        mock_wheel.mBrakeTemp = 100.0
        mock_wheel.mTemperature = [300.0, 300.0, 300.0]
        mock_tele.mWheels = [mock_wheel] * 4

        mock_scor = MagicMock()
        mock_scor.mDriverName = b'David Dean'
        mock_scor.mVehicleName = b'BMW M4 GT3'
        mock_scor.mTotalLaps = 1
        mock_scor.mLapDist = 0.0

        # At lap start: mTimeIntoLap should be 0.0 (fixed in v0.2.1)
        mock_scor.mTimeIntoLap = 0.0
        mock_scor.mCurSector1 = 0.0
        mock_scor.mCurSector2 = 0.0

        mock_scor_info = MagicMock()
        mock_scor_info.mTrackName = b'Sebring'
        mock_scor_info.mLapDist = 5954.0
        mock_scor_info.mTrackTemp = 25.0
        mock_scor_info.mAmbientTemp = 20.0
        mock_scor_info.mSession = 5

        mock_api.playersVehicleTelemetry.return_value = mock_tele
        mock_api.playersVehicleScoring.return_value = mock_scor
        mock_api.Rf2Scor.mScoringInfo = mock_scor_info
        mock_api.isSharedMemoryAvailable.return_value = True

        from src.telemetry.telemetry_real import RealTelemetryReader

        reader = RealTelemetryReader()
        data = reader.read()

        # At lap start, lap_time should be 0.0
        assert data['lap_time'] == pytest.approx(0.0, abs=0.001), \
            f"Expected lap_time=0.0s at lap start, got {data['lap_time']}s"
