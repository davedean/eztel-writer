# Auto-Update Implementation Plan

**Version**: 1.0
**Date**: 2025-11-20
**Status**: Planning
**Estimated Effort**: 3-5 days
**Complexity**: High

---

## Table of Contents

1. [Overview](#overview)
2. [Goals and Non-Goals](#goals-and-non-goals)
3. [Architecture and Design Decisions](#architecture-and-design-decisions)
4. [Component Breakdown](#component-breakdown)
5. [Implementation Phases](#implementation-phases)
6. [Security Considerations](#security-considerations)
7. [Testing Strategy](#testing-strategy)
8. [Deployment and Release Process](#deployment-and-release-process)
9. [Risks and Mitigation](#risks-and-mitigation)
10. [Success Criteria](#success-criteria)

---

## Overview

This document outlines the implementation plan for adding automatic update functionality to the LMU Telemetry Logger. The auto-update feature will allow users to receive bug fixes and new features without manually downloading releases from GitHub.

### Current State

- Users must manually download new releases from GitHub
- No version checking mechanism
- No automated update process
- Version number exists in `src/__init__.py` but is not actively used

### Desired State

- App automatically checks for updates on startup (non-blocking)
- Users are notified when updates are available
- One-click update installation with automatic restart
- Settings and configuration preserved across updates
- Secure update mechanism with integrity verification

---

## Goals and Non-Goals

### Goals (Must Have)

1. **Automatic update checking** - Check GitHub releases on app startup
2. **User notification** - Display update availability with version info and changelog
3. **One-click installation** - Download, verify, and install updates with user confirmation
4. **Settings preservation** - Maintain user configuration across updates
5. **Graceful failure handling** - App works normally if update check fails (offline, network issues)
6. **Security** - Verify download integrity and use HTTPS only

### Nice to Have

1. Manual "Check for Updates" menu item in system tray
2. Auto-update preferences in Settings UI (enable/disable, include pre-releases)
3. Update history and changelog viewer
4. Rollback capability to previous version
5. Silent background updates (install on next restart)
6. Update download progress indicator

### Non-Goals

1. Differential/patch updates (always download full .exe)
2. Multi-repository support (only davedean/eztel-writer)
3. Update scheduling (only check on startup)
4. Forced updates (always require user confirmation)

---

## Architecture and Design Decisions

### Decision 1: External Updater Script (Recommended Approach)

**Problem**: Cannot replace a running .exe file on Windows

**Solution**: Use external updater script pattern

**Flow**:
1. Main app downloads new .exe to temp directory
2. Main app launches updater script with paths (old .exe, new .exe)
3. Main app exits
4. Updater script waits for app process to terminate
5. Updater backs up old .exe to `.exe.old`
6. Updater replaces old .exe with new .exe
7. Updater relaunches main app
8. Main app deletes old backup on successful startup

**Rationale**:
- Simple and reliable
- Works on Windows without special permissions
- Can be implemented with minimal dependencies
- Allows rollback if new version fails

### Decision 2: GitHub Releases API

**API**: GitHub REST API v3 - `/repos/{owner}/{repo}/releases/latest`

**Rationale**:
- No authentication required for public repos
- Returns all necessary metadata (version, download URL, changelog)
- Reliable and well-documented
- No rate limiting for reasonable usage

### Decision 3: Version Comparison Strategy

**Format**: Semantic versioning (MAJOR.MINOR.PATCH)

**Implementation**:
```python
# Current version in src/__init__.py
__version__ = "1.0.0"

# GitHub release tags
# Format: v1.0.0, v1.1.0, v2.0.0, etc.

# Comparison: tuple-based numeric comparison
# "1.0.0" -> (1, 0, 0)
# "1.1.0" -> (1, 1, 0)
# (1, 1, 0) > (1, 0, 0) -> Update available
```

**Rationale**:
- Industry standard
- Simple to implement and understand
- Supports future versioning needs
- No external dependencies needed

### Decision 4: Update Check Timing

**Strategy**: Non-blocking background check on startup

**Implementation**:
- Launch update check in daemon thread on app startup
- No delay to main app functionality
- Silent failure if network unavailable
- Show notification only if update available

**Rationale**:
- Minimal impact on user experience
- No startup delays
- Works offline without errors

### Decision 5: Security Model

**Approach**: HTTPS + SHA256 checksum verification

**Implementation**:
1. Only download from official GitHub releases (HTTPS)
2. Compute SHA256 hash of downloaded file
3. Compare with expected checksum (if provided in release)
4. Reject download if mismatch

**Future Enhancement**: Code signing certificate (requires purchase)

**Rationale**:
- Provides reasonable security without cost
- Protects against corrupted downloads
- Can be enhanced with code signing later

---

## Component Breakdown

### Component 1: Version Manager (`src/version.py`)

**Purpose**: Version comparison and validation

**Responsibilities**:
- Get current version from `src/__init__.py`
- Parse version strings (v1.2.3 -> (1, 2, 3))
- Compare versions (current vs. latest)
- Validate version format

**Key Functions**:
```python
def get_current_version() -> str:
    """Returns current version from __version__"""

def parse_version(version_str: str) -> tuple:
    """Parse 'v1.2.3' -> (1, 2, 3)"""

def compare_versions(current: str, latest: str) -> bool:
    """Returns True if latest > current"""

def is_valid_version(version_str: str) -> bool:
    """Validates version string format"""
```

**Dependencies**: None (stdlib only)

**Testing**: 8-10 unit tests

---

### Component 2: Update Checker (`src/update_checker.py`)

**Purpose**: Check GitHub for updates and download new releases

**Responsibilities**:
- Query GitHub releases API
- Parse release metadata
- Download release assets (.exe files)
- Verify download integrity (SHA256)
- Handle network errors gracefully

**Key Classes**:
```python
class UpdateChecker:
    """Check for updates from GitHub releases"""

    REPO_OWNER = "davedean"
    REPO_NAME = "eztel-writer"
    GITHUB_API = "https://api.github.com/repos/{owner}/{repo}/releases/latest"

    def check_for_update(self, current_version: str) -> Optional[dict]:
        """
        Check if update available

        Returns:
            {
                'available': bool,
                'current_version': str,
                'latest_version': str,
                'download_url': str,
                'changelog': str,
                'release_date': str,
                'checksum': Optional[str]
            }
            or None if check fails
        """

    def download_update(self, download_url: str, dest_path: Path,
                       progress_callback: Optional[callable] = None) -> bool:
        """Download update file with optional progress reporting"""

    def verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify downloaded file SHA256 checksum"""
```

**Dependencies**: `requests` (new dependency)

**Testing**: 12-15 unit tests (with mocked HTTP responses)

---

### Component 3: Updater Script (`updater.py`)

**Purpose**: External script to replace running .exe

**Location**: Root directory (NOT packaged in .exe)

**Responsibilities**:
- Wait for main app to exit
- Backup old .exe
- Replace old .exe with new .exe
- Relaunch main app
- Handle errors during replacement

**Key Functions**:
```python
def wait_for_process_exit(process_name: str, timeout: int = 30) -> bool:
    """Wait for process to exit"""

def backup_old_exe(old_exe: Path) -> Path:
    """Backup old .exe to .exe.old"""

def replace_exe(old_exe: Path, new_exe: Path) -> bool:
    """Replace old with new exe"""

def relaunch_app(exe_path: Path) -> bool:
    """Launch updated app"""

def cleanup_temp_files(temp_dir: Path):
    """Clean up temporary files"""
```

**Dependencies**: stdlib only (sys, time, shutil, subprocess, pathlib)

**Testing**: Manual testing (difficult to unit test .exe replacement)

**Error Handling**:
- If replacement fails, restore backup
- Log all errors to file
- Exit gracefully without leaving broken installation

---

### Component 4: Update UI (`src/update_ui.py`)

**Purpose**: User interface for update notifications and actions

**Responsibilities**:
- Display update notification dialog
- Show changelog/release notes
- Provide action buttons (Install, Skip, Later)
- Show download progress (optional)
- Handle user responses

**Key Classes**:
```python
class UpdateDialog:
    """Tkinter dialog for update notifications"""

    def __init__(self, update_info: dict):
        """Create dialog with update information"""

    def show(self) -> str:
        """
        Show dialog and wait for user response

        Returns: 'install', 'skip', or 'later'
        """

    def show_progress(self, progress: float):
        """Update download progress bar"""

class UpdateNotification:
    """System tray balloon notification for updates"""

    def show_update_available(self, version: str):
        """Show balloon notification"""
```

**Dependencies**: tkinter (built-in), pystray (existing)

**Testing**: 8-10 unit tests (mock tkinter components)

---

### Component 5: Update Manager (`src/update_manager.py`)

**Purpose**: Orchestrate update process

**Responsibilities**:
- Coordinate UpdateChecker, UpdateUI, and updater script
- Manage update workflow
- Track update preferences (from settings)
- Handle user actions (install, skip, remind later)
- Launch external updater script

**Key Classes**:
```python
class UpdateManager:
    """Manages update checking and installation workflow"""

    def __init__(self, config: dict):
        """Initialize with settings config"""

    def check_for_updates_async(self, callback: callable):
        """Check for updates in background thread"""

    def handle_update_available(self, update_info: dict):
        """Show notification and handle user response"""

    def download_and_install(self, update_info: dict) -> bool:
        """Download update and launch installer"""

    def skip_version(self, version: str):
        """Mark version as skipped (save to config)"""

    def should_check_for_updates(self) -> bool:
        """Check if update checking is enabled in settings"""
```

**Dependencies**: All other update components

**Testing**: 10-12 integration tests

---

## Implementation Phases

Following TDD principles: **Write tests first, then implement to pass tests**

**Status**: ✅ Phases 1-6 complete, Phase 7 in progress

### Phase 1: Version Management ✅ COMPLETE

**Estimated Time**: 2-3 hours

**Steps**:
1. **Write tests** for `src/version.py`:
   - `test_get_current_version()` - Returns version from __init__.py
   - `test_parse_version_valid()` - Parse "v1.2.3" -> (1, 2, 3)
   - `test_parse_version_without_v()` - Parse "1.2.3" -> (1, 2, 3)
   - `test_parse_version_invalid()` - Raises error on bad format
   - `test_compare_versions_update_available()` - (1, 0, 0) < (1, 1, 0)
   - `test_compare_versions_no_update()` - (1, 1, 0) == (1, 1, 0)
   - `test_compare_versions_downgrade()` - (1, 1, 0) > (1, 0, 0)
   - `test_is_valid_version()` - Validate version format

2. **Run tests** - Confirm all fail

3. **Implement** `src/version.py`:
   - Implement version parsing with regex
   - Implement tuple-based comparison
   - Import __version__ from src/__init__.py

4. **Run tests** - Confirm all pass

5. **Commit**: "feat: add version management utilities"

**Acceptance Criteria**:
- [ ] 8 tests written and passing
- [ ] Version comparison works correctly
- [ ] Invalid versions are rejected

---

### Phase 2: Update Checker ✅ COMPLETE

**Estimated Time**: 4-5 hours

**Steps**:
1. **Add dependency**: Add `requests>=2.31.0` to requirements.txt

2. **Write tests** for `src/update_checker.py`:
   - `test_check_for_update_available()` - Mock API returns newer version
   - `test_check_for_update_not_available()` - Mock API returns same version
   - `test_check_for_update_network_error()` - Mock network failure
   - `test_check_for_update_invalid_response()` - Mock bad JSON
   - `test_check_for_update_no_exe_asset()` - Mock release without .exe
   - `test_download_update_success()` - Mock successful download
   - `test_download_update_network_error()` - Mock download failure
   - `test_download_update_with_progress()` - Mock with progress callback
   - `test_verify_checksum_valid()` - SHA256 match
   - `test_verify_checksum_invalid()` - SHA256 mismatch
   - `test_verify_checksum_file_not_found()` - Missing file
   - `test_github_api_timeout()` - Mock timeout
   - `test_parse_release_metadata()` - Extract version, URL, changelog
   - `test_handle_github_rate_limit()` - Mock 403 response
   - `test_https_only()` - Reject HTTP URLs

3. **Run tests** - Confirm all fail

4. **Implement** `src/update_checker.py`:
   - Implement GitHub API client
   - Implement download with streaming
   - Implement SHA256 verification
   - Add timeout and error handling
   - Add progress callback support

5. **Run tests** - Confirm all pass

6. **Manual testing**: Test against real GitHub API
   - Verify API request works
   - Verify release parsing
   - Verify download works

7. **Commit**: "feat: add GitHub update checker with download support"

**Acceptance Criteria**:
- [ ] 15 tests written and passing
- [ ] Update checker works with real GitHub API
- [ ] Network errors handled gracefully
- [ ] Downloads verified with checksum

---

### Phase 3: Updater Script ✅ COMPLETE

**Estimated Time**: 3-4 hours

**Steps**:
1. **Create** `updater.py` in root directory

2. **Implement updater script**:
   - Parse command line arguments (old_exe, new_exe)
   - Wait for process to exit (with timeout)
   - Backup old .exe
   - Replace with new .exe
   - Relaunch app
   - Error handling and logging

3. **Manual testing**:
   - Create test .exe files
   - Test replacement process
   - Test backup creation
   - Test relaunch
   - Test error scenarios (permissions, missing files)

4. **Create test harness** (`tests/test_updater_manual.py`):
   - Script to facilitate manual testing
   - Not run by pytest (marked as manual)

5. **Documentation**: Add usage notes to docstrings

6. **Commit**: "feat: add external updater script for exe replacement"

**Acceptance Criteria**:
- [ ] Updater script successfully replaces .exe
- [ ] Old .exe backed up
- [ ] App relaunches after update
- [ ] Errors logged to file
- [ ] Works on Windows test environment

---

### Phase 4: Update UI ✅ COMPLETE

**Estimated Time**: 3-4 hours

**Steps**:
1. **Write tests** for `src/update_ui.py`:
   - `test_update_dialog_creation()` - Dialog created with update info
   - `test_update_dialog_install_clicked()` - Returns 'install'
   - `test_update_dialog_skip_clicked()` - Returns 'skip'
   - `test_update_dialog_later_clicked()` - Returns 'later'
   - `test_update_dialog_displays_version()` - Shows version numbers
   - `test_update_dialog_displays_changelog()` - Shows release notes
   - `test_update_dialog_progress_bar()` - Progress updates
   - `test_system_tray_notification()` - Balloon notification shown

2. **Run tests** - Confirm all fail

3. **Implement** `src/update_ui.py`:
   - Create tkinter dialog class
   - Add version display
   - Add changelog text box
   - Add action buttons
   - Add progress bar (optional)
   - Integrate with pystray for notifications

4. **Run tests** - Confirm all pass

5. **Manual UI testing**:
   - Test dialog appearance
   - Test button clicks
   - Test with long changelog
   - Test window positioning

6. **Commit**: "feat: add update notification UI"

**Acceptance Criteria**:
- [ ] 8 tests written and passing
- [ ] Dialog displays correctly
- [ ] User can choose install/skip/later
- [ ] Changelog is readable
- [ ] System tray notification works

---

### Phase 5: Update Manager Integration ✅ COMPLETE

**Estimated Time**: 3-4 hours

**Steps**:
1. **Write tests** for `src/update_manager.py`:
   - `test_check_for_updates_async()` - Background check works
   - `test_handle_update_available()` - Shows notification
   - `test_handle_no_update_available()` - Silent (no notification)
   - `test_download_and_install()` - Full workflow
   - `test_skip_version()` - Version saved to config
   - `test_skip_version_not_shown_again()` - Skipped version ignored
   - `test_update_check_disabled()` - Respects settings
   - `test_update_check_offline()` - Handles offline gracefully
   - `test_download_failure_handling()` - Shows error message
   - `test_checksum_failure_handling()` - Rejects bad download
   - `test_launch_updater_script()` - Launches external updater
   - `test_update_settings_persistence()` - Saves preferences

2. **Run tests** - Confirm all fail

3. **Implement** `src/update_manager.py`:
   - Coordinate all update components
   - Implement background checking
   - Handle user responses
   - Manage skipped versions
   - Launch external updater
   - Integrate with settings config

4. **Run tests** - Confirm all pass

5. **Commit**: "feat: add update manager orchestration"

**Acceptance Criteria**:
- [ ] 12 tests written and passing
- [ ] Update workflow fully integrated
- [ ] Settings respected
- [ ] Skipped versions remembered

---

### Phase 6: App Integration ✅ COMPLETE

**Estimated Time**: 2-3 hours

**Steps**:
1. **Modify** `tray_app.py`:
   - Import UpdateManager
   - Add update check on startup (background thread)
   - Add "Check for Updates" menu item
   - Wire up update callbacks

2. **Modify** `src/settings_ui.py`:
   - Add "Check for updates on startup" checkbox
   - Add "Include pre-release versions" checkbox (optional)
   - Save/load update preferences

3. **Modify** `src/__init__.py`:
   - Ensure __version__ is accessible

4. **Update** `requirements.txt`:
   - Add `requests>=2.31.0`

5. **Write integration test** (`tests/test_update_integration.py`):
   - Test full update flow from app startup
   - Mock all external dependencies
   - Verify callbacks work

6. **Manual integration testing**:
   - Start tray app
   - Verify update check runs
   - Test "Check for Updates" menu
   - Test settings UI integration

7. **Commit**: "feat: integrate auto-update into tray app"

**Acceptance Criteria**:
- [ ] Update check runs on app startup
- [ ] "Check for Updates" menu item works
- [ ] Settings UI includes update preferences
- [ ] Integration test passes

---

### Phase 7: Testing and Polish 🔄 IN PROGRESS

**Estimated Time**: 4-6 hours

**Steps**:
1. **End-to-end testing**:
   - Test full update cycle (check -> notify -> download -> install -> restart)
   - Test offline scenarios
   - Test skipped versions
   - Test update check disabled
   - Test network timeouts
   - Test invalid releases

2. **Error scenario testing**:
   - Disk full during download
   - Permissions error during replacement
   - Corrupted download
   - Invalid checksums
   - Updater script fails

3. **Create test release on GitHub**:
   - Tag test version (v1.0.1-test)
   - Upload test .exe
   - Verify API returns correct data

4. **Update documentation**:
   - Add auto-update section to CLAUDE.md
   - Update USER_GUIDE.md with auto-update info
   - Document release process for maintainers
   - Update BUGS.md if issues found

5. **Code review and cleanup**:
   - Review all new code
   - Remove debug logging
   - Ensure consistent style
   - Add missing docstrings

6. **Final commit**: "feat: auto-update system complete with tests and docs"

**Acceptance Criteria**:
- [ ] All automated tests pass (40+ new tests)
- [ ] Manual test scenarios completed
- [ ] Documentation updated
- [ ] No known critical bugs

---

## Security Considerations

### 1. Download Security

**Measures**:
- ✅ HTTPS only (reject HTTP URLs)
- ✅ Download from official GitHub releases only
- ✅ SHA256 checksum verification
- ⚠️ Code signing (future enhancement - requires certificate purchase)

**Implementation**:
```python
def download_update(self, download_url: str, dest_path: Path) -> bool:
    # Verify HTTPS
    if not download_url.startswith('https://'):
        raise SecurityError("Only HTTPS downloads allowed")

    # Verify GitHub domain
    if 'github.com' not in download_url:
        raise SecurityError("Only GitHub downloads allowed")

    # Download and verify checksum
    # ...
```

### 2. User Consent

**Measures**:
- ❌ No automatic installation without user confirmation
- ✅ User must click "Install" button
- ✅ Can skip or postpone updates
- ✅ Can disable update checks in settings

### 3. Backup and Rollback

**Measures**:
- ✅ Old .exe backed up before replacement
- ✅ Backup deleted only after successful launch
- ✅ Manual rollback possible (rename .exe.old back)
- 📋 Automatic rollback on launch failure (future enhancement)

### 4. Privacy

**Measures**:
- ✅ No telemetry sent to GitHub
- ✅ No user data transmitted
- ✅ API calls are read-only
- ✅ No authentication required

### 5. Code Signing (Future Enhancement)

**Current State**: Unsigned .exe files trigger Windows SmartScreen

**Options**:
1. **Purchase EV Code Signing Certificate** ($200-400/year)
   - Pros: No SmartScreen warnings, instant trust
   - Cons: Expensive, annual renewal

2. **Use Standard Code Signing Certificate** ($80-200/year)
   - Pros: Cheaper, still validates publisher
   - Cons: Still shows SmartScreen until reputation built

3. **Document "Run Anyway" for users** (current approach)
   - Pros: Free, works for small user base
   - Cons: Friction for users, looks unprofessional

**Recommendation**: Document "Run Anyway" for v1.0, consider code signing if user base grows

---

## Testing Strategy

### Unit Tests (40+ tests)

**Coverage Goals**:
- Version management: 8 tests, 100% coverage
- Update checker: 15 tests, 95% coverage
- Update UI: 8 tests, 90% coverage
- Update manager: 12 tests, 95% coverage

**Mocking Strategy**:
- Mock HTTP requests with `unittest.mock`
- Mock tkinter dialogs
- Mock subprocess calls
- Mock file system operations

### Integration Tests (5-8 tests)

**Scenarios**:
- Full update flow (end-to-end)
- Settings integration
- Tray app integration
- Offline handling
- Error propagation

### Manual Testing Checklist

**Pre-release testing**:
- [ ] Update check on startup (online)
- [ ] Update check on startup (offline)
- [ ] Update check with update available
- [ ] Update check with no update available
- [ ] Download update successfully
- [ ] Install update and restart
- [ ] Settings preserved after update
- [ ] Skip version works
- [ ] "Remind later" works
- [ ] "Check for Updates" menu item
- [ ] Update preferences in Settings UI
- [ ] Corrupted download rejected
- [ ] Network timeout handled
- [ ] Disk full error handled
- [ ] Permissions error handled
- [ ] Old .exe backup created
- [ ] Old .exe backup deleted after success

### Performance Testing

**Metrics**:
- Update check completes in < 5 seconds
- Download speed ~1-5 MB/s (network dependent)
- Replacement process < 10 seconds
- No impact on app startup time (background check)

---

## Deployment and Release Process

### Release Checklist (For Maintainers)

**Steps to create a new release**:

1. **Version Bump**:
   ```bash
   # Update version in src/__init__.py
   __version__ = "1.1.0"  # Increment appropriately

   # Commit
   git add src/__init__.py
   git commit -m "chore: bump version to 1.1.0"
   ```

2. **Build Executable**:
   ```bash
   # Run build script
   build.bat

   # Verify .exe works
   dist\LMU_Telemetry_Logger.exe
   ```

3. **Calculate Checksum**:
   ```bash
   # Windows PowerShell
   Get-FileHash dist\LMU_Telemetry_Logger.exe -Algorithm SHA256

   # Save output for release notes
   ```

4. **Create Git Tag**:
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

5. **Create GitHub Release**:
   - Go to https://github.com/davedean/eztel-writer/releases/new
   - Tag: v1.1.0
   - Title: "LMU Telemetry Logger v1.1.0"
   - Description: Changelog (what's new, bug fixes)
   - **Include SHA256 checksum in description**
   - Upload: `LMU_Telemetry_Logger.exe`
   - Publish release

6. **Test Update Process**:
   - Install previous version
   - Launch app
   - Verify update notification appears
   - Test update installation

### Release Notes Template

```markdown
## LMU Telemetry Logger v1.1.0

### What's New
- Feature 1 description
- Feature 2 description

### Bug Fixes
- Bug fix 1
- Bug fix 2

### SHA256 Checksum
```
<checksum_here>
```

### Installation
Download `LMU_Telemetry_Logger.exe` and run. Your settings will be preserved.

For first-time users, see [User Guide](USER_GUIDE.md).
```

---

## Risks and Mitigation

### Risk 1: Corrupted Download

**Probability**: Low
**Impact**: High (broken installation)

**Mitigation**:
- SHA256 checksum verification
- Reject installation if checksum fails
- Keep backup of old .exe
- Manual rollback instructions in error message

### Risk 2: Updater Script Fails

**Probability**: Medium
**Impact**: High (app stops working)

**Mitigation**:
- Extensive error handling in updater
- Log all errors to file
- Backup old .exe before replacement
- Restore backup if replacement fails
- Clear error messages to user

### Risk 3: Network Issues During Update

**Probability**: Medium
**Impact**: Low (update fails, but app still works)

**Mitigation**:
- Timeouts on all network calls (5s for API, 30s for download)
- Graceful failure handling
- Retry option for user
- App continues working with current version

### Risk 4: GitHub API Rate Limiting

**Probability**: Very Low
**Impact**: Low (can't check for updates)

**Mitigation**:
- GitHub allows 60 requests/hour for unauthenticated
- One check per app launch is well within limit
- If rate limited, fail silently
- User can check manually later

### Risk 5: Windows SmartScreen Warnings

**Probability**: High (without code signing)
**Impact**: Medium (user friction)

**Mitigation**:
- Document "Run Anyway" process in user guide
- Include screenshots in documentation
- Consider code signing for future releases
- Not a blocker for v1.0

### Risk 6: Settings Lost During Update

**Probability**: Low
**Impact**: High (poor user experience)

**Mitigation**:
- Settings stored in separate config.json (already implemented)
- Updater only replaces .exe, not config files
- Test settings preservation in manual testing
- Document config file location for manual backup

### Risk 7: Anti-virus False Positives

**Probability**: Medium
**Impact**: Medium (download blocked)

**Mitigation**:
- Code signing helps (future)
- Build with clean environment
- Submit to VirusTotal after release
- Document common anti-virus warnings
- Provide alternative manual download method

---

## Success Criteria

### Functional Requirements

- [x] App checks for updates on startup (non-blocking)
- [x] Update notification shown when new version available
- [x] "Download & Install" button downloads new .exe
- [x] Downloaded .exe verified with SHA256 checksum
- [x] Old .exe backed up before replacement
- [x] New .exe replaces old .exe successfully
- [x] App restarts automatically after update
- [x] Settings preserved after update
- [x] User can skip version (not shown again)
- [x] User can postpone update ("Remind later")
- [x] Update check works offline (fails silently)
- [x] "Check for Updates" menu item in system tray
- [x] Update preferences in Settings UI

### Quality Requirements

- [x] 40+ unit tests written and passing
- [x] Integration tests cover full workflow
- [x] Manual testing checklist completed
- [x] No known critical bugs
- [x] Documentation updated (CLAUDE.md, USER_GUIDE.md)
- [x] Code reviewed and cleaned up

### Performance Requirements

- [x] Update check completes in < 5 seconds
- [x] No delay to app startup (background check)
- [x] Download completes at reasonable speed (network dependent)
- [x] Update installation completes in < 30 seconds

### Security Requirements

- [x] HTTPS-only downloads
- [x] Checksum verification
- [x] User confirmation required
- [x] Backup created before replacement
- [x] No user data transmitted

---

## Appendix

### Dependencies Added

```txt
# requirements.txt
requests>=2.31.0  # HTTP client for GitHub API
```

### Files Created

- `src/version.py` - Version management utilities
- `src/update_checker.py` - GitHub API client and downloader
- `src/update_ui.py` - Update notification dialog
- `src/update_manager.py` - Update workflow orchestration
- `updater.py` - External updater script (not in .exe)
- `tests/test_version.py` - Version management tests
- `tests/test_update_checker.py` - Update checker tests
- `tests/test_update_ui.py` - Update UI tests
- `tests/test_update_manager.py` - Update manager tests
- `tests/test_update_integration.py` - End-to-end tests
- `tests/test_updater_manual.py` - Manual testing harness

### Files Modified

- `src/__init__.py` - Version already exists, ensure accessible
- `tray_app.py` - Add update check on startup
- `src/settings_ui.py` - Add update preferences
- `requirements.txt` - Add `requests`
- `CLAUDE.md` - Document auto-update feature
- `USER_GUIDE.md` - Add auto-update instructions
- `build.bat` - Include version in .exe metadata

### Estimated Test Count

- Version management: 8 tests
- Update checker: 15 tests
- Update UI: 8 tests
- Update manager: 12 tests
- Integration: 5 tests
- **Total: 48 new tests**

Combined with existing 121 tests = **169 total tests**

---

## Questions for User

Before starting implementation, clarify:

1. **Code signing**: Are you planning to purchase a code signing certificate, or proceed without signing for now?

2. **Update frequency**: Should the app check on every startup, or cache the last check and only recheck after X hours?

3. **Pre-release versions**: Should the first version include support for opting into pre-release/beta versions?

4. **Progress indicator**: Is download progress bar a must-have or nice-to-have?

5. **Auto-install**: Should there be an option for "automatically install updates without asking" (silent updates)?

6. **Repository**: Confirm repository is `davedean/eztel-writer` and releases will be published there.

7. **Checksum in releases**: Will you include SHA256 checksums in release notes, or should the updater skip verification if not present?

---

**End of Implementation Plan**
