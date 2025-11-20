## Status: FIXED ✅
**Priority:** Medium
**Fixed:** 2025-11-20

---

## Original Issue

I noticed I have to start the writer _after_ LMU has started, otherwise the call to the rest-api fails and we fallback to using only the shared memory api.

I think we should:

- detect the process
- _then_ try the rest-api (if we don't already have what we need, or its >24hrs old for example)
- if the rest-api call fails, we could try again later, eg: when ready to save a file

we could also check for "unenriched" csv files and enrich them, if we successfully manage to reach the rest-api. I don't know what a good trigger for that would be, we could raise another bug for it if its better dealt with seperately.

---

## Solution Implemented

**Changes Made:**

1. **`src/telemetry/telemetry_real.py`** - Modified REST API initialization:
   - No longer sets `rest_api = None` if initially unavailable
   - Added `_rest_api_checked` flag to track fetch attempts
   - Added `_try_fetch_vehicle_data()` method for safe fetch attempts
   - Added `ensure_rest_api_data()` method for deferred retry logic

2. **`example_app.py`** - Added retry call before enrichment:
   - Calls `ensure_rest_api_data()` before using REST API for player laps
   - Ensures vehicle metadata is available even if writer started before LMU

3. **`src/telemetry/telemetry_real.py`** - Added retry for opponent tracking:
   - `get_all_vehicles()` now calls `ensure_rest_api_data()` before enrichment
   - Opponent laps get enriched even if REST API wasn't available at startup

**How It Works:**

- On initialization, REST API client is created but doesn't fail if LMU not running
- When lap data needs enrichment, `ensure_rest_api_data()` is called
- This method checks if data was already fetched; if not, tries again
- Subsequent laps will have enriched metadata once LMU REST API becomes available

**Result:**
- ✅ Writer can be started before or after LMU starts
- ✅ REST API enrichment happens automatically when LMU becomes available
- ✅ No manual restart required
- ✅ All 93 tests pass

**Future Enhancement:**
The suggestion to enrich existing "unenriched" CSV files could be tracked as a separate enhancement request.
