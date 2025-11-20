# Bug: Opponent Lap Files Missing Lap Time in Filename

## Status: ✅ RESOLVED

**Resolved:** 2025-11-20
**Commit:** b1ddf34
**Branch:** claude/fix-filename-bugs-01CLu94YJxeArb1fd83FLuPj

**Solution:** Changed opponent filename format in `tray_app.py` from `{session_id}_{track}_{car}_{driver}_fastest.csv` to `{session_id}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv`. Opponent files now show lap number and time in filename, matching player file format.

---

## Summary
Opponent lap files use a filename format that doesn't include the lap time, making it difficult to identify lap performance at a glance. The format should match player lap files which include `lap{lap}_t{lap_time}s` in the filename.

## Current Behavior
**Opponent lap filename** (set in `tray_app.py:226`):
```python
opponent_filename_format = '{session_id}_{track}_{car}_{driver}_fastest.csv'
```

Example filename:
```
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_fastest.csv
```

**Player lap filename** (default in `file_manager.py:32-34`):
```python
filename_format = '{date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'
```

Example filename:
```
2024-11-20_14-30_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap3_t94s.csv
```

## Problem
- Opponent files don't show lap number or lap time in filename
- Can't quickly identify which lap or how fast without opening file
- `_fastest.csv` suffix is static and doesn't indicate actual lap time
- Inconsistent with player lap file naming convention

## Expected Behavior
Opponent lap files should include lap number and lap time, similar to player files:

```python
opponent_filename_format = '{session_id}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'
```

Example improved filename:
```
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap8_t94s.csv
```

## Benefits of Including Lap Time
1. **Quick identification** - See lap time without opening file
2. **Performance comparison** - Easily compare opponent lap times at a glance
3. **Consistency** - Matches player lap file format
4. **Sorting** - Files sort naturally by lap time when alphabetically sorted
5. **Historical tracking** - If saving multiple laps per opponent in future, lap times distinguish them

## Root Cause
The opponent filename format is hardcoded in `tray_app.py:226`:

```python
opponent_filename_format = '{session_id}_{track}_{car}_{driver}_fastest.csv'
```

This format:
- Was designed for "fastest lap only" strategy (thus `_fastest` suffix)
- Doesn't use `{lap}` or `{lap_time}` placeholders
- Is passed to `FileManager.save_lap()` which formats the filename

## Proposed Solution

### Change 1: Update Filename Format in `tray_app.py`
```python
# OLD (line 226)
opponent_filename_format = '{session_id}_{track}_{car}_{driver}_fastest.csv'

# NEW
opponent_filename_format = '{session_id}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'
```

### Change 2: Ensure lap_summary Contains Required Fields
In `tray_app.py:221-224`, verify `lap_summary` has lap number and time:

```python
lap_summary = {
    'lap': opponent_lap_data.lap_number,
    'lap_time': opponent_lap_data.lap_time,
}
```

This already looks correct.

### Change 3: Test FileManager Formatting
The `FileManager._generate_filename()` method should already support `{lap}` and `{lap_time}` placeholders (see `file_manager.py:126-135`).

## Files to Modify
- `/home/user/eztel-writer/tray_app.py:226` - Change opponent filename format

## Testing
1. Run application in multiplayer session
2. Wait for opponent to complete a lap
3. Check output directory for opponent lap file
4. Verify filename includes:
   - Session ID (e.g., `20241120143052`)
   - Track name (e.g., `road-atlanta`)
   - Car name (e.g., `hypercar_cadillac-v-series-r`)
   - Driver name (e.g., `john-smith`)
   - Lap number (e.g., `lap8`)
   - Lap time in seconds (e.g., `t94s`)
5. Verify format: `{session_id}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv`

## Example Before/After

### Before
```
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_fastest.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_jane-doe_fastest.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_bob-jones_fastest.csv
```

Problems:
- No lap time visible
- All files end with `_fastest.csv` (redundant, not informative)
- Can't quickly compare performance

### After
```
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap8_t94s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_jane-doe_lap8_t92s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_bob-jones_lap8_t96s.csv
```

Benefits:
- Lap time immediately visible (94s, 92s, 96s)
- Can quickly see Jane was fastest (92s)
- Consistent with player lap file format
- Lap number shown for context

## Priority
**Medium** - Quality of life improvement. Current behavior works but is not user-friendly.

## Related Issues
- Related to `bug_player_filename_format_inconsistency.md` - overall filename format improvements
- May help with `bug_multiple_opponent_laps_captured.md` - lap time in filename makes duplicates more obvious

## Related Files
- `/home/user/eztel-writer/tray_app.py:226` - Opponent filename format
- `/home/user/eztel-writer/src/file_manager.py:126-135` - Filename generation logic
- `/home/user/eztel-writer/tray_app.py:221-224` - lap_summary construction
