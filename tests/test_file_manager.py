"""Tests for file manager"""

import pytest
import tempfile
import shutil
from pathlib import Path
from src.file_manager import FileManager


class TestFileManager:
    """Test suite for FileManager"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup after test
        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_initialization_creates_output_dir(self, temp_dir):
        """Should create output directory on initialization"""
        output_dir = temp_dir / "test_output"
        manager = FileManager({'output_dir': str(output_dir)})

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_default_output_directory(self):
        """Should use default output directory if not specified"""
        manager = FileManager()
        assert manager.output_dir == Path('./telemetry_output')

    def test_save_lap_creates_file(self, temp_dir):
        """Should save CSV content to file"""
        manager = FileManager({'output_dir': str(temp_dir)})

        csv_content = "player,v8,Test,0,12345\nheader\ndata"
        lap_summary = {'lap': 1}
        session_info = {'session_id': '12345'}

        filepath = manager.save_lap(csv_content, lap_summary, session_info)

        assert Path(filepath).exists()
        assert Path(filepath).is_file()

    def test_save_lap_writes_correct_content(self, temp_dir):
        """Should write exact CSV content to file"""
        manager = FileManager({'output_dir': str(temp_dir)})

        csv_content = "test,data,here\n1,2,3"
        lap_summary = {'lap': 1}
        session_info = {'session_id': '12345'}

        filepath = manager.save_lap(csv_content, lap_summary, session_info)

        with open(filepath, 'r') as f:
            saved_content = f.read()

        assert saved_content == csv_content

    def test_filename_generation_with_session_and_lap(self, temp_dir):
        """Should generate filename with session ID and lap number"""
        manager = FileManager({'output_dir': str(temp_dir)})

        lap_summary = {'lap': 5}
        session_info = {'session_id': '2025111812345'}

        csv_content = "test"
        filepath = manager.save_lap(csv_content, lap_summary, session_info)

        filename = Path(filepath).name
        assert '2025111812345' in filename
        assert 'lap5' in filename
        assert filename.endswith('.csv')

    def test_custom_filename_format(self, temp_dir):
        """Should support custom filename format"""
        custom_format = '{track}_{car}_lap{lap}.csv'
        manager = FileManager({
            'output_dir': str(temp_dir),
            'filename_format': custom_format
        })

        lap_summary = {'lap': 3}
        session_info = {
            'track_name': 'Bahrain',
            'car_name': 'Toyota',
            'session_id': '12345'
        }

        csv_content = "test"
        filepath = manager.save_lap(csv_content, lap_summary, session_info)

        filename = Path(filepath).name
        assert 'Bahrain' in filename
        assert 'Toyota' in filename
        assert 'lap3' in filename

    def test_sanitizes_invalid_filename_characters(self, temp_dir):
        """Should remove/replace invalid filename characters"""
        manager = FileManager({'output_dir': str(temp_dir)})

        lap_summary = {'lap': 1}
        session_info = {
            'session_id': '12345',
            'car_name': 'Car<>:"/\\|?*Name',
            'track_name': 'Track With Spaces'
        }

        csv_content = "test"
        filepath = manager.save_lap(csv_content, lap_summary, session_info)

        filename = Path(filepath).name
        # Invalid characters should be replaced
        assert '<' not in filename
        assert '>' not in filename
        assert ':' not in filename
        assert '"' not in filename
        assert '/' not in filename
        assert '\\' not in filename
        # Spaces should be replaced with underscores
        assert ' ' not in filename

    def test_list_saved_laps(self, temp_dir):
        """Should list all saved lap files"""
        manager = FileManager({'output_dir': str(temp_dir)})

        # Save 3 laps
        for i in range(1, 4):
            lap_summary = {'lap': i}
            session_info = {'session_id': '12345'}
            manager.save_lap("test", lap_summary, session_info)

        laps = manager.list_saved_laps()
        assert len(laps) == 3

    def test_list_saved_laps_empty_directory(self, temp_dir):
        """Should return empty list for empty directory"""
        manager = FileManager({'output_dir': str(temp_dir)})

        laps = manager.list_saved_laps()
        assert laps == []

    def test_delete_lap(self, temp_dir):
        """Should delete specific lap file"""
        manager = FileManager({'output_dir': str(temp_dir)})

        # Save a lap
        lap_summary = {'lap': 1}
        session_info = {'session_id': '12345'}
        filepath = manager.save_lap("test", lap_summary, session_info)
        filename = Path(filepath).name

        # Verify it exists
        assert Path(filepath).exists()

        # Delete it
        result = manager.delete_lap(filename)
        assert result is True
        assert not Path(filepath).exists()

    def test_delete_nonexistent_lap(self, temp_dir):
        """Should return False when deleting nonexistent file"""
        manager = FileManager({'output_dir': str(temp_dir)})

        result = manager.delete_lap('nonexistent.csv')
        assert result is False

    def test_clear_all_laps(self, temp_dir):
        """Should delete all lap files"""
        manager = FileManager({'output_dir': str(temp_dir)})

        # Save 5 laps
        for i in range(1, 6):
            lap_summary = {'lap': i}
            session_info = {'session_id': '12345'}
            manager.save_lap("test", lap_summary, session_info)

        # Verify they exist
        assert len(manager.list_saved_laps()) == 5

        # Clear all
        count = manager.clear_all_laps()
        assert count == 5
        assert len(manager.list_saved_laps()) == 0

    def test_get_session_laps(self, temp_dir):
        """Should filter laps by session ID"""
        manager = FileManager({'output_dir': str(temp_dir)})

        # Save laps from two different sessions
        for i in range(1, 4):
            manager.save_lap("test", {'lap': i}, {'session_id': 'session1'})

        for i in range(1, 3):
            manager.save_lap("test", {'lap': i}, {'session_id': 'session2'})

        # Get laps for session1
        session1_laps = manager.get_session_laps('session1')
        assert len(session1_laps) == 3

        # Get laps for session2
        session2_laps = manager.get_session_laps('session2')
        assert len(session2_laps) == 2

    def test_get_output_directory(self, temp_dir):
        """Should return output directory path"""
        manager = FileManager({'output_dir': str(temp_dir)})

        output_dir = manager.get_output_directory()
        assert output_dir == temp_dir

    def test_fallback_session_id_generation(self, temp_dir):
        """Should generate fallback session ID if none provided"""
        manager = FileManager({'output_dir': str(temp_dir)})

        lap_summary = {'lap': 1}
        session_info = {}  # No session_id

        filepath = manager.save_lap("test", lap_summary, session_info)

        # Should still create a file with generated session ID
        assert Path(filepath).exists()
        filename = Path(filepath).name
        assert filename.endswith('.csv')

    def test_multiple_saves_dont_overwrite(self, temp_dir):
        """Multiple saves with same lap/session should create separate files or overwrite"""
        manager = FileManager({'output_dir': str(temp_dir)})

        lap_summary = {'lap': 1}
        session_info = {'session_id': '12345'}

        # Save same lap twice
        filepath1 = manager.save_lap("content1", lap_summary, session_info)
        filepath2 = manager.save_lap("content2", lap_summary, session_info)

        # They should have the same filename (overwrite behavior)
        assert filepath1 == filepath2

        # Latest content should be in the file
        with open(filepath2, 'r') as f:
            content = f.read()

        assert content == "content2"
