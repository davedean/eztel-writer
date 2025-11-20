# Bug: Player Lap Filename Format Inconsistency

## Status: ✅ RESOLVED

**Resolved:** 2025-11-20
**Commit:** b1ddf34
**Branch:** claude/fix-filename-bugs-01CLu94YJxeArb1fd83FLuPj

**Solution:** Changed default filename format in `src/file_manager.py` from `{date}_{time}_` prefix to `{session_id}_` prefix. All player and opponent files now use consistent session_id-based naming.

---

## Summary
Player lap files and opponent lap files use inconsistent filename formats. Player files include a date/time prefix, while opponent files start with session_id. This makes it harder to group files from the same session and creates unnecessary inconsistency.

## Current Behavior

### Player Lap Filename
Default format (from `file_manager.py:32-34`):
```python
'{date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'
```

Example:
```
2024-11-20_14-30_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap3_t94s.csv
```

### Opponent Lap Filename
Custom format (from `tray_app.py:226`):
```python
'{session_id}_{track}_{car}_{driver}_fastest.csv'
```

Example (current):
```
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_jane-doe_fastest.csv
```

Example (after fixing bug_opponent_filename_missing_laptime.md):
```
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_jane-doe_lap8_t92s.csv
```

## Problem
1. **Inconsistent format** - Player files start with date/time, opponent files start with session_id
2. **Sorting issues** - Files from same session don't sort together
3. **Date/time redundancy** - Date and time are already in session_id (which is a timestamp: `20241120143052` = 2024-11-20 14:30:52)
4. **Harder to group** - Can't easily identify all files from one session
5. **Different prefixes** - Player uses `2024-11-20_14-30`, opponent uses `20241120143052`

## Expected Behavior
All lap files (player and opponent) should use the same filename format:
- Start with `session_id` (identifies the session)
- Followed by metadata (track, car, driver)
- End with lap number and time
- No separate date/time prefix (redundant with session_id)

## Proposed Solution

### Change Player Filename Format
Modify the default filename format in `file_manager.py`:

```python
# OLD (line 32-34)
self.filename_format = self.config.get(
    'filename_format',
    '{date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'
)

# NEW
self.filename_format = self.config.get(
    'filename_format',
    '{session_id}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'
)
```

### Result: Consistent Filenames

#### Player Laps
```
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap1_t96s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap2_t95s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap3_t94s.csv
```

#### Opponent Laps
```
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_jane-doe_lap8_t92s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_bob-jones_lap8_t96s.csv
```

#### Benefits
- **All files from same session start with same session_id** (e.g., `20241120143052_`)
- **Easy to filter**: `ls 20241120143052_*` shows all files from that session
- **Alphabetical sorting groups by session**, then track, then car, then driver, then lap
- **Consistent format** between player and opponent files
- **No redundancy** - session_id contains date/time information
- **Human-readable** - session_id `20241120143052` → 2024-11-20 14:30:52

## Session ID Format
The session_id is generated as a timestamp:

```python
# From session_manager.py
session_id = datetime.now().strftime("%Y%m%d%H%M%S")
# Example: "20241120143052" = 2024-11-20 14:30:52
```

This format:
- Sortable (alphabetical = chronological)
- Unique per session (includes second precision)
- Compact (14 characters)
- Human-decodable (YYYYMMDDHHMMSS)

## Files to Modify
1. `/home/user/eztel-writer/src/file_manager.py:32-34` - Change default filename format
2. `/home/user/eztel-writer/tests/test_file_manager.py` - Update tests to expect new format

## Migration Considerations

### Backward Compatibility
This is a **breaking change** for users who:
- Have existing telemetry files with old format
- Have scripts that parse filenames expecting `{date}_{time}_` prefix
- Use the date/time prefix for sorting or filtering

### Migration Strategy
1. **Update default** - New installations use new format
2. **Config override** - Users who want old format can set in `config.json`:
   ```json
   {
     "filename_format": "{date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv"
   }
   ```
3. **Documentation** - Update USER_GUIDE.md to explain format change

### Testing Old Format
The old format should still work if explicitly configured:
```python
# User can override in config.json
FileManager({
    'filename_format': '{date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'
})
```

## Testing
1. Run application (both player and multiplayer)
2. Complete at least one player lap
3. Wait for at least one opponent lap
4. Check output directory:
   - All files should start with same session_id
   - Player files: `{session_id}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv`
   - Opponent files: `{session_id}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv`
5. Verify alphabetical sorting groups files correctly:
   - By session (all same session together)
   - Then by track
   - Then by car
   - Then by driver
   - Then by lap number

## Example File Listing

### Before (Current)
```
2024-11-20_14-30_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap1_t96s.csv
2024-11-20_14-30_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap2_t95s.csv
2024-11-20_14-30_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap3_t94s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_jane-doe_fastest.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_bob-jones_fastest.csv
```

Problems:
- Different prefixes (date vs session_id)
- Hard to see which files belong together
- Opponent files sort separately from player files

### After (Proposed)
```
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_bob-jones_lap8_t96s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_jane-doe_lap8_t92s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap1_t96s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap2_t95s.csv
20241120143052_road-atlanta_hypercar_cadillac-v-series-r_john-smith_lap3_t94s.csv
```

Benefits:
- All files from session `20241120143052` grouped together
- Consistent format across all lap files
- Easy to filter: `ls 20241120143052_*`
- Natural sorting by driver, then lap number

## Priority
**Medium** - Quality of life improvement. Current behavior works but creates inconsistency and makes file management harder.

## Related Issues
- Related to `bug_opponent_filename_missing_laptime.md` - both issues improve filename consistency
- Part of overall file naming standardization effort

## Related Files
- `/home/user/eztel-writer/src/file_manager.py:32-34` - Default filename format
- `/home/user/eztel-writer/src/file_manager.py:88-140` - Filename generation logic
- `/home/user/eztel-writer/tray_app.py:226` - Opponent filename format
- `/home/user/eztel-writer/tests/test_file_manager.py` - Tests to update
