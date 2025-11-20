#!/usr/bin/env python
"""External updater script for LMU Telemetry Logger

This script handles replacing the running .exe with a new version.
It must be run as a separate process, not packaged in the main .exe.

Usage:
    python updater.py <old_exe_path> <new_exe_path>

Process:
    1. Wait for old app process to exit
    2. Backup old .exe to .exe.old
    3. Replace old .exe with new .exe
    4. Relaunch updated app
    5. Clean up and exit

All errors are logged to updater.log in the same directory as the script.
"""

import sys
import time
import shutil
import logging
import subprocess
from pathlib import Path


# Configure logging
log_file = Path(__file__).parent / 'updater.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def wait_for_process_exit(process_name: str, timeout: int = 30) -> bool:
    """Wait for a process to exit.

    Args:
        process_name: Name of the process to wait for (e.g., 'LMU_Telemetry_Logger.exe')
        timeout: Maximum time to wait in seconds

    Returns:
        bool: True if process exited, False if timeout
    """
    try:
        import psutil
    except ImportError:
        # If psutil not available, just wait a fixed time
        logger.warning("psutil not available, using fixed 5 second delay")
        time.sleep(5)
        return True

    start_time = time.time()
    process_name_lower = process_name.lower()

    logger.info(f"Waiting for process '{process_name}' to exit (timeout: {timeout}s)...")

    while time.time() - start_time < timeout:
        # Check if process is still running
        found = False
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and process_name_lower in proc.info['name'].lower():
                    found = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not found:
            logger.info(f"Process '{process_name}' has exited")
            return True

        time.sleep(0.5)

    logger.error(f"Timeout waiting for process '{process_name}' to exit")
    return False


def backup_old_exe(old_exe: Path) -> bool:
    """Backup old .exe file.

    Args:
        old_exe: Path to old .exe file

    Returns:
        bool: True if backup successful, False otherwise
    """
    backup_path = old_exe.with_suffix('.exe.old')

    try:
        # Remove existing backup if present
        if backup_path.exists():
            logger.info(f"Removing existing backup: {backup_path}")
            backup_path.unlink()

        # Create backup
        logger.info(f"Backing up {old_exe} to {backup_path}")
        shutil.copy2(old_exe, backup_path)

        logger.info("Backup created successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to backup old exe: {e}")
        return False


def replace_exe(old_exe: Path, new_exe: Path) -> bool:
    """Replace old .exe with new .exe.

    Args:
        old_exe: Path to old .exe file (will be replaced)
        new_exe: Path to new .exe file (will be moved to old location)

    Returns:
        bool: True if replacement successful, False otherwise
    """
    try:
        # Verify new exe exists
        if not new_exe.exists():
            logger.error(f"New exe not found: {new_exe}")
            return False

        # Remove old exe
        if old_exe.exists():
            logger.info(f"Removing old exe: {old_exe}")
            old_exe.unlink()

        # Move new exe to old location
        logger.info(f"Moving {new_exe} to {old_exe}")
        shutil.move(str(new_exe), str(old_exe))

        logger.info("Replacement successful")
        return True

    except Exception as e:
        logger.error(f"Failed to replace exe: {e}")

        # Attempt to restore backup
        backup_path = old_exe.with_suffix('.exe.old')
        if backup_path.exists() and not old_exe.exists():
            logger.info("Attempting to restore backup...")
            try:
                shutil.copy2(backup_path, old_exe)
                logger.info("Backup restored successfully")
            except Exception as restore_error:
                logger.error(f"Failed to restore backup: {restore_error}")

        return False


def relaunch_app(exe_path: Path) -> bool:
    """Relaunch the updated application.

    Args:
        exe_path: Path to .exe file to launch

    Returns:
        bool: True if launch successful, False otherwise
    """
    try:
        logger.info(f"Relaunching application: {exe_path}")

        # Launch as detached process
        if sys.platform == 'win32':
            # Windows: use CREATE_NEW_PROCESS_GROUP to detach
            subprocess.Popen(
                [str(exe_path)],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                close_fds=True
            )
        else:
            # Unix-like systems
            subprocess.Popen(
                [str(exe_path)],
                start_new_session=True,
                close_fds=True
            )

        logger.info("Application relaunched successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to relaunch application: {e}")
        return False


def cleanup_temp_files(temp_dir: Path):
    """Clean up temporary files.

    Args:
        temp_dir: Directory containing temporary files
    """
    try:
        if temp_dir.exists() and temp_dir.is_dir():
            logger.info(f"Cleaning up temp directory: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Failed to clean up temp files: {e}")


def main():
    """Main updater function."""
    logger.info("=" * 60)
    logger.info("LMU Telemetry Logger Updater")
    logger.info("=" * 60)

    # Parse command line arguments
    if len(sys.argv) < 3:
        logger.error("Usage: updater.py <old_exe> <new_exe>")
        print("Usage: updater.py <old_exe> <new_exe>", file=sys.stderr)
        sys.exit(1)

    old_exe_path = Path(sys.argv[1]).resolve()
    new_exe_path = Path(sys.argv[2]).resolve()

    logger.info(f"Old exe: {old_exe_path}")
    logger.info(f"New exe: {new_exe_path}")

    # Validate paths
    if not new_exe_path.exists():
        logger.error(f"New exe not found: {new_exe_path}")
        sys.exit(1)

    # Wait for old app to exit
    process_name = old_exe_path.name
    if not wait_for_process_exit(process_name, timeout=30):
        logger.error("Failed to wait for old process to exit")
        sys.exit(1)

    # Additional safety delay
    time.sleep(2)

    # Backup old exe
    if not backup_old_exe(old_exe_path):
        logger.error("Failed to backup old exe")
        sys.exit(1)

    # Replace exe
    if not replace_exe(old_exe_path, new_exe_path):
        logger.error("Failed to replace exe")
        sys.exit(1)

    # Relaunch app
    if not relaunch_app(old_exe_path):
        logger.error("Failed to relaunch application")
        sys.exit(1)

    # Clean up temp directory containing new exe
    temp_dir = new_exe_path.parent
    if 'temp' in str(temp_dir).lower():
        cleanup_temp_files(temp_dir)

    logger.info("Update completed successfully!")
    logger.info("=" * 60)

    # Exit updater
    sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
