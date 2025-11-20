# CSV Data Quality Issues

## Status: RESOLVED ✅
**Priority:** Medium
**Complexity:** Low-Medium
**Fixed:** 2025-11-20

---

## Resolution Summary

All issues have been resolved in the current codebase:

1. ✅ **Issue 1 (TrackLen = 0.00)**: FIXED - Both `MockTelemetryReader` and `RealTelemetryReader` now correctly populate `track_length` in `session_info`. Verified with tests showing track_length = 5386.80.

2. ✅ **Issue 2 (LapTime repetition)**: FIXED - LapTime column removed from data rows. Format upgraded to LMUTelemetry v3 with 10 columns instead of 12. LapTime now appears only in metadata section.

3. ✅ **Issue 3 (Sector always 0)**: FIXED - Sectors now calculate correctly when track_length is available. The root cause was Issue 1 (track_length = 0), which has been resolved.

4. ✅ **Issue 4 (Y elevation)**: FIXED - Y [m] column removed from data rows. Format now uses 10 columns for more efficient storage.

**Testing**: All 93 tests pass, including CSV formatter tests validating the v3 format.

---

## Original Issue Report (Historical Reference)

## Observed Issues

### Metadata Section
```
Format	LMUTelemetry v2
Version	1
Player	Dean Davids
TrackName	Algarve International Circuit
CarName	The Bend Team WRT 2025 #31:LM
SessionUTC	2025-11-18T13:52:51Z
LapTime [s]	302.325043
TrackLen [m]	0.00          ← ISSUE 1: Always 0.00
GameVersion	1.0
Event	Practice
```

**Issue 1:** `TrackLen [m]` is always `0.00`
- Should contain actual track length from session_info
- Currently defaults to 0.0 when track_length not available
- Impacts: sector calculation, data analysis

**Note:** Sector times (Sector1Time, Sector2Time, Sector3Time) are already being added to metadata when available ✅

### Telemetry Data Section
```
LapDistance [m]	LapTime [s]	Sector [int]	Speed [km/h]	EngineRevs [rpm]	...
260.344	        302.325	    0	        0.00	    1740.59	        ...
882.076	        302.325	    0	        100.07	    5042.36	        ...
2867.300	    302.325	    0	        145.60	    5911.45	        ...
3685.692	    302.325	    0	        178.11	    5906.33	        ...
```

**Issue 2:** `LapTime [s]` repeated on every row (always 302.325)
- Wasteful - lap time is already in metadata
- This should be time-since-lap-start (incrementing) OR removed entirely
- Impact: ~10% file size reduction if removed

**Issue 3:** `Sector [int]` always 0
- Sector calculation depends on valid track_length (see Issue 1)
- When track_length is 0, sector defaults to 0
- Should calculate from lap_distance / track_length
- Impact: Sector column is useless until track_length is fixed

**Issue 4:** `Y [m]` column (elevation) may not be needed
- Y coordinate is elevation in game's Y-up coordinate system
- X and Z provide lateral position (horizontal plane)
- Consider: Do we need 3D position or just 2D track position?
- Impact: ~8% file size reduction if removed

---

## Root Cause Analysis

### Issue 1: TrackLen = 0.00
**Location:** `src/mvp_format.py:201-208`

```python
track_length = _first_float(
    session_info.get("TrackLen [m]"),
    session_info.get("track_length"),
    _max_sample_value(lap_samples, "LapDistance [m]"),
    default=0.0,
    require_positive=True,
)
```

**Problem:**
- `session_info` doesn't contain `track_length` key
- Falls back to max lap_distance, but `require_positive=True` may reject valid values
- Check: Does telemetry reader populate `track_length` in session_info?

**Files to check:**
- `src/telemetry/telemetry_mock.py` - Mock reader session_info
- `src/telemetry/telemetry_real.py` - Real reader session_info
- `example_app.py` - How session_info is passed

### Issue 2: LapTime Repetition
**Location:** `src/mvp_format.py:11-24` (header), `src/mvp_format.py:47-48` (normalization)

**Current behavior:** Stores total lap time on every sample

**Options:**
1. Remove `LapTime [s]` from data columns entirely (already in metadata)
2. Change to incremental time-since-lap-start
3. Keep as-is but document purpose

**Recommendation:** Option 1 (remove) - simplest, reduces file size

### Issue 3: Sector Always 0
**Location:** `src/mvp_format.py:148-166` (_resolve_sector)

**Dependency:** Requires Issue 1 to be fixed first

**Logic:**
```python
if track_length > 0.0:
    progress = max(0.0, min(0.9999, lap_distance / track_length))
    return int(progress * 3)  # Split into 3 sectors
return 0
```

**Should work once track_length is populated correctly.**

### Issue 4: Elevation (Y) Storage
**Location:** `src/mvp_format.py:11-24` (header), `src/mvp_format.py:74-75` (normalization)

**Current:** Stores X, Y, Z coordinates
**Question:** Is elevation needed for telemetry analysis/visualization?

**Options:**
1. Remove Y [m] column entirely
2. Make elevation optional (suppress when not needed)
3. Keep as-is

**Decision needed:** Check with user on use case

---

## Implementation Plan

### Phase 1: Fix Track Length (Fixes Issues 1 & 3)
**Files:** `src/telemetry/telemetry_mock.py`, `src/telemetry/telemetry_real.py`, `example_app.py`

**Steps:**
1. Verify `track_length` is in telemetry reader's `get_session_info()` output
   - Mock: Check line 28-29 has `track_length` key
   - Real: Check if shared memory provides track length
2. Update `example_app.py` to ensure session_info includes track_length
3. Add test to verify track_length appears in metadata
4. Verify sector calculation works once track_length > 0

**Estimated effort:** 1 hour
**Test coverage:** Add test for track_length in metadata

### Phase 2: Remove LapTime from Data Rows (Fixes Issue 2)
**Files:** `src/mvp_format.py`, `src/csv_formatter.py`, `tests/test_csv_formatter.py`, `tests/test_sample_normalizer.py`

**Steps:**
1. Remove `"LapTime [s]"` from `MVP_TELEMETRY_HEADER` list
2. Remove lap_time from `SampleNormalizer.normalize()` return dict
3. Update CSV formatter to handle 11 columns instead of 12
4. Update all tests expecting 12-column format
5. Update example.csv reference file
6. Document in CHANGELOG

**Estimated effort:** 2 hours
**Test coverage:** Update existing CSV format tests

**Breaking change:** Yes - changes CSV format from 12 to 11 columns

### Phase 3: Consider Elevation Removal (Issue 4)
**Decision point:** Requires user input

**If removing Y [m]:**
- Remove from header (down to 10 columns)
- Update normalization logic
- Update tests

**If keeping:**
- Document the Y-up coordinate system
- No changes needed

**Estimated effort:** 1 hour (if removing)

---

## Testing Requirements

### New Tests Needed
1. `test_track_length_in_metadata()` - Verify TrackLen populated from session_info
2. `test_sector_calculation_with_track_length()` - Verify sectors 0,1,2 calculated correctly
3. `test_csv_format_11_columns()` - Verify LapTime removed from data rows
4. `test_laptime_only_in_metadata()` - Verify total lap time still in metadata

### Integration Tests
1. Run example_app and verify:
   - TrackLen [m] > 0 in output CSV
   - Sector values transition 0→1→2 during lap
   - LapTime only in metadata, not data rows
   - File size ~10% smaller

---

## Acceptance Criteria

✅ TrackLen [m] shows actual track length, not 0.00
✅ Sector [int] values are 0, 1, or 2 (not always 0)
✅ LapTime [s] appears only in metadata, not in data rows
✅ All 72 tests passing
✅ File size reduced by ~10-18%
✅ Backward compatibility: Old CSVs still readable

---

## Migration Notes

**Format Change:** If LapTime removed from data rows:
- Old format: 12 columns in data section
- New format: 11 columns in data section
- Metadata section unchanged (still has LapTime [s])
- Parsers expecting 12 columns will need update

**Recommendation:** Bump format version to "LMUTelemetry v3" if removing LapTime column
