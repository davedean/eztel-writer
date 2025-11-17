"""File management for saving telemetry CSV files"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class FileManager:
    """
    Manages file operations for telemetry CSV files

    Responsibilities:
    - Generate unique filenames
    - Save CSV data to disk
    - Manage output directory structure
    - Handle file naming conventions
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize file manager

        Args:
            config: Configuration dictionary with optional keys:
                - output_dir: Base directory for output files (default: "./telemetry_output")
                - filename_format: Format string for filenames (default: "{session_id}_lap{lap}.csv")
        """
        self.config = config or {}
        self.output_dir = Path(self.config.get('output_dir', './telemetry_output'))
        self.filename_format = self.config.get('filename_format', '{session_id}_lap{lap}.csv')

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_lap(
        self,
        csv_content: str,
        lap_summary: Dict[str, Any],
        session_info: Dict[str, Any]
    ) -> str:
        """
        Save lap data to CSV file

        Args:
            csv_content: Complete CSV content as string
            lap_summary: Lap summary data (contains lap number)
            session_info: Session metadata (contains session_id)

        Returns:
            Path to saved file as string
        """
        filename = self._generate_filename(lap_summary, session_info)
        filepath = self.output_dir / filename

        # Write CSV content to file
        with open(filepath, 'w') as f:
            f.write(csv_content)

        return str(filepath)

    def _generate_filename(
        self,
        lap_summary: Dict[str, Any],
        session_info: Dict[str, Any]
    ) -> str:
        """
        Generate filename for lap data

        Args:
            lap_summary: Lap summary (contains lap number)
            session_info: Session info (contains session_id, car, track, etc.)

        Returns:
            Filename string
        """
        lap = lap_summary.get('lap', 0)
        session_id = session_info.get('session_id', self._generate_fallback_session_id())

        # Additional fields that might be useful in filename
        car = session_info.get('car_name', '')
        track = session_info.get('track_name', '')

        # Format filename using format string
        filename = self.filename_format.format(
            session_id=session_id,
            lap=lap,
            car=car,
            track=track
        )

        # Sanitize filename (remove invalid characters)
        filename = self._sanitize_filename(filename)

        return filename

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing invalid characters

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscores
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Replace spaces with underscores
        filename = filename.replace(' ', '_')

        return filename

    def _generate_fallback_session_id(self) -> str:
        """Generate a fallback session ID if none provided"""
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def get_output_directory(self) -> Path:
        """Get the output directory path"""
        return self.output_dir

    def list_saved_laps(self) -> list[str]:
        """
        List all saved lap files in output directory

        Returns:
            List of filenames
        """
        if not self.output_dir.exists():
            return []

        return [f.name for f in self.output_dir.glob('*.csv')]

    def delete_lap(self, filename: str) -> bool:
        """
        Delete a specific lap file

        Args:
            filename: Name of file to delete

        Returns:
            True if deleted, False if file not found
        """
        filepath = self.output_dir / filename

        if filepath.exists():
            filepath.unlink()
            return True

        return False

    def clear_all_laps(self) -> int:
        """
        Delete all lap files in output directory

        Returns:
            Number of files deleted
        """
        count = 0

        for filepath in self.output_dir.glob('*.csv'):
            filepath.unlink()
            count += 1

        return count

    def get_session_laps(self, session_id: str) -> list[str]:
        """
        Get all lap files for a specific session

        Args:
            session_id: Session ID to filter by

        Returns:
            List of filenames for this session
        """
        if not self.output_dir.exists():
            return []

        pattern = f"*{session_id}*.csv"
        return [f.name for f in self.output_dir.glob(pattern)]
