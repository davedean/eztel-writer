# Bug: No "Settings" Menu Option in System Tray

**Status**: 🐛 OPEN
**Priority**: Medium
**Category**: User Interface
**Related Feature**: Phase 5 (System Tray UI), Settings UI
**Date Reported**: 2025-11-20

---

## Description

The Settings UI (`src/settings_ui.py`) was implemented and works via command-line flag (`--settings`), but there is no menu option to access it from the system tray. Users running the app via `tray_app.py` have no way to change settings without restarting the app with the `--settings` flag.

**Current**: System tray menu has Start/Stop, Pause/Resume, Open Folder, Check for Updates, and Quit
**Expected**: System tray menu should include a "Settings..." option to open the settings dialog

## Steps to Reproduce

1. Run `python tray_app.py`
2. Right-click on the system tray icon
3. Look at the menu options

**Actual Result**: No "Settings" or "Preferences" option visible in the menu

**Expected Result**: A "Settings..." menu item that opens the settings dialog when clicked

## Impact

- Users cannot access settings while the app is running in system tray mode
- Forces users to:
  - Quit the app
  - Restart with `--settings` flag
  - Edit `config.json` manually
- Poor user experience for configuration changes

## Technical Details

### Current System Tray Menu (src/tray_ui.py:74-89)

```python
menu = pystray.Menu(
    Item(
        self._get_start_stop_text,
        self.on_start_stop
    ),
    Item(
        self._get_pause_resume_text,
        self.on_pause_resume,
        enabled=self._is_pause_resume_enabled
    ),
    Item('Open Output Folder', self.on_open_folder),
    pystray.Menu.SEPARATOR,
    Item('Check for Updates...', self.on_check_for_updates),
    pystray.Menu.SEPARATOR,
    Item('Quit', self.on_quit)
)
```

### Missing Integration

The Settings UI exists and works:
- ✅ `src/settings_ui.py` - Implemented
- ✅ `SettingsConfig` - Backend configuration management
- ✅ `SettingsDialog` - tkinter GUI dialog
- ✅ Command-line flag works: `python tray_app.py --settings`
- ❌ **No menu item in system tray**
- ❌ **No `on_settings()` handler in TrayUI class**

## Suggested Fix

Add a "Settings..." menu item between "Open Output Folder" and "Check for Updates":

```python
menu = pystray.Menu(
    Item(
        self._get_start_stop_text,
        self.on_start_stop
    ),
    Item(
        self._get_pause_resume_text,
        self.on_pause_resume,
        enabled=self._is_pause_resume_enabled
    ),
    Item('Open Output Folder', self.on_open_folder),
    pystray.Menu.SEPARATOR,
    Item('Settings...', self.on_settings),  # NEW
    Item('Check for Updates...', self.on_check_for_updates),
    pystray.Menu.SEPARATOR,
    Item('Quit', self.on_quit)
)
```

And implement the handler:

```python
def on_settings(self):
    """Handle Settings menu click"""
    from src.settings_ui import show_settings_dialog

    # Show settings dialog (will block until closed)
    changed = show_settings_dialog()

    # If settings changed, optionally notify user to restart
    # (or implement hot-reload if possible)
    if changed:
        # TODO: Decide if restart is needed or if we can hot-reload
        pass
```

## Workaround

Users can currently:
1. Quit the app
2. Run `python tray_app.py --settings`
3. Configure settings in the dialog
4. Click Save
5. Run `python tray_app.py` normally

Or edit `config.json` manually.

## Related Files

- `src/tray_ui.py` - System tray menu (needs modification)
- `src/settings_ui.py` - Settings dialog (already implemented)
- `tray_app.py` - System tray entry point
- `tests/test_tray_ui.py` - Tests for tray UI (needs test for settings menu)

## Acceptance Criteria

- [ ] "Settings..." menu item visible in system tray menu
- [ ] Clicking "Settings..." opens the settings dialog
- [ ] Settings dialog is functional when opened from tray
- [ ] Changed settings are saved to `config.json`
- [ ] Menu item positioned logically (between "Open Folder" and "Check for Updates")
- [ ] Test added to `test_tray_ui.py` for settings menu handler

## Notes

- Consider whether settings changes require app restart or can be hot-reloaded
- Settings dialog uses tkinter, should work cross-platform
- May need threading consideration (settings dialog might block tray thread)
- Standard placement: Settings typically appear near the bottom of tray menus, before Quit

---

**Next Steps**: Add "Settings..." menu item to `TrayUI` class and implement `on_settings()` handler
