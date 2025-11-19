**STATUS: RESOLVED**

**Issue:** We were saving all laps, including incomplete ones (out laps, partial laps where session closes, teleports to pits, etc.)

**Solution:** Modified `example_app.py` to check `lap_summary['lap_completed']` flag before saving. Incomplete laps are now discarded and not written to disk.

**Changes:**
- `example_app.py`: Added check for `lap_completed` flag in `on_lap_complete()` callback
- `tests/test_example_app_integration.py`: Added 4 integration tests to verify filtering behavior
- `tests/test_telemetry_loop.py`: Added 3 tests to verify lap_completed flag is set correctly

**Test coverage:**
- Complete laps (normal lap transitions) → saved
- Incomplete laps (idle timeout) → discarded
- Incomplete laps (lap distance reset/teleport) → discarded
- Lap counter only increments for complete laps

All 72 tests passing ✓

---

**Original requirements:**
we should discard incomplete laps, eg: if we didn't start them by crossing the start line, and end them by crossing the finish line.

eg: discard out laps, discard partial laps (where we close the game/session) etc
