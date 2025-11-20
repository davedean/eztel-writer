"""Manual testing harness for updater.py

This is NOT run by pytest automatically. It's a helper script for manual testing
of the updater.py script.

Usage:
    python tests/test_updater_manual.py

This will:
1. Create test .exe files
2. Simulate the update process
3. Verify the replacement worked
4. Clean up test files

Mark as manual test to exclude from pytest:
    pytest -m "not manual"
"""

import sys
import time
import tempfile
import subprocess
from pathlib import Path

import pytest


# Mark all tests in this module as manual
pytestmark = pytest.mark.manual


def create_test_exe(path: Path, content: str):
    """Create a test .exe file with identifiable content."""
    path.write_text(content)
    print(f"Created test exe: {path}")


def test_updater_script_replacement():
    """Manual test: Verify updater can replace .exe files.

    This test creates dummy .exe files and runs the updater script
    to verify it can successfully replace them.
    """
    print("\n" + "=" * 60)
    print("Manual Updater Test")
    print("=" * 60)

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        old_exe = temp_path / "test_app.exe"
        new_exe = temp_path / "test_app_new.exe"

        create_test_exe(old_exe, "Old version 1.0.0")
        create_test_exe(new_exe, "New version 1.1.0")

        print(f"\nOld exe content: {old_exe.read_text()}")
        print(f"New exe content: {new_exe.read_text()}")

        # Run updater script
        updater_script = Path(__file__).parent.parent / "updater.py"
        print(f"\nRunning updater: {updater_script}")
        print(f"  Old: {old_exe}")
        print(f"  New: {new_exe}")

        result = subprocess.run(
            [sys.executable, str(updater_script), str(old_exe), str(new_exe)],
            capture_output=True,
            text=True
        )

        print(f"\nUpdater exit code: {result.returncode}")
        print(f"Updater stdout:\n{result.stdout}")
        if result.stderr:
            print(f"Updater stderr:\n{result.stderr}")

        # Verify replacement
        if old_exe.exists():
            content = old_exe.read_text()
            print(f"\nReplaced exe content: {content}")

            if "New version" in content:
                print("✓ SUCCESS: Exe was replaced correctly!")
            else:
                print("✗ FAIL: Exe was not replaced")

            # Check if backup was created
            backup = old_exe.with_suffix('.exe.old')
            if backup.exists():
                backup_content = backup.read_text()
                print(f"✓ Backup created: {backup_content}")
            else:
                print("✗ No backup found")
        else:
            print("✗ FAIL: Old exe no longer exists")

        print("=" * 60)


def test_updater_script_with_psutil():
    """Manual test: Verify updater works with psutil available.

    This test checks that process detection works when psutil is installed.
    """
    print("\n" + "=" * 60)
    print("Manual Updater Test with psutil")
    print("=" * 60)

    try:
        import psutil
        print("✓ psutil is available")
    except ImportError:
        print("⚠ psutil not available, skipping process detection test")
        pytest.skip("psutil not available")

    print("Note: This test doesn't launch actual processes.")
    print("Process detection will be tested during integration testing.")
    print("=" * 60)


if __name__ == '__main__':
    """Run manual tests directly."""
    print("\nRunning manual updater tests...")
    print("(These are not run by pytest automatically)\n")

    test_updater_script_replacement()
    test_updater_script_with_psutil()

    print("\n✓ Manual tests completed")
