# Session ID and Build Stamp Implementation

## Summary

Added two key features to improve debugging and deployment tracking:

### 1. Session ID for Log Tracking

**Problem:** When multiple users are active, performance logs get interleaved making it hard to track individual user sessions.

**Solution:** Each user session now gets a unique 8-character session ID that prefixes all performance logs.

**Implementation:**
- Session ID generated on first page load using `uuid.uuid4()[:8]`
- Stored in `st.session_state.session_id` (persists across page reloads)
- All PERF logs now include `[session_id]` prefix
- Passed to `get_user_investment_metrics()` function for nested logging

**Example Logs:**
```
[a1b2c3d4] PERF: Starting dashboard data load
[a1b2c3d4] PERF: get_current_positions took 0.15s
[e5f6g7h8] PERF: Starting dashboard data load  ← Different user
[a1b2c3d4] PERF: get_user_investment_metrics took 10.5s
[e5f6g7h8] PERF: get_user_investment_metrics took 9.8s
```

**Benefits:**
- Easy filtering: `grep "[a1b2c3d4]" logs.txt`
- Track individual user performance
- Identify if slowness is user-specific or system-wide
- Debug race conditions and concurrent access issues

### 2. Build Stamp Display

**Problem:** No easy way to know which version of code is deployed or when it was built.

**Solution:** Display build timestamp from Woodpecker CI on the admin page (same as main page footer).

**Implementation:**

The build timestamp is set by Woodpecker CI during deployment:

1. **Woodpecker CI** (`.woodpecker.yml`):
   - Generates `BUILD_TIMESTAMP` from `CI_PIPELINE_STARTED`
   - Formats in Pacific Time: `2025-12-16 07:26 PST`
   - Passes as environment variable to Docker container

2. **Admin Page Display**:
   - Reads `os.getenv("BUILD_TIMESTAMP")`
   - Shows in header: `🏷️ Build: 2025-12-16 07:26 PST`
   - Falls back to "Development" with current time if not set

**Woodpecker CI Configuration:**
```yaml
# .woodpecker.yml (lines 38-46)
- |
  if [ -n "$CI_PIPELINE_STARTED" ]; then
    export BUILD_TIMESTAMP=$(TZ=America/Vancouver date -d "@$CI_PIPELINE_STARTED" "+%Y-%m-%d %H:%M %Z")
  else
    export BUILD_TIMESTAMP=$(TZ=America/Vancouver date "+%Y-%m-%d %H:%M %Z")
  fi

# Docker run command (line 65)
docker run -d ... -e BUILD_TIMESTAMP="$BUILD_TIMESTAMP" ... trading-dashboard:latest
```

**Benefits:**
- Know exactly when the current deployment was built
- Verify deployments completed successfully
- Same timestamp shown on both main page footer and admin page
- Automatically set by CI/CD - no manual steps needed

## Files Modified

### Performance Logging with Session ID:
- `web_dashboard/streamlit_app.py` - Added session ID generation and logging
- `web_dashboard/streamlit_utils.py` - Updated `get_user_investment_metrics()` to accept and use session_id
- `PERFORMANCE_LOGGING.md` - Updated documentation with session ID examples

### Build Timestamp Display:
- `web_dashboard/pages/admin.py` - Display `BUILD_TIMESTAMP` env var in header
- `.woodpecker.yml` - Already configured to set `BUILD_TIMESTAMP` (no changes needed)
- `SESSION_ID_AND_BUILD_STAMP.md` - Documentation

## Integration with CI/CD

**No changes needed!** The build timestamp is already integrated with Woodpecker CI.

The `.woodpecker.yml` file already:
1. Generates `BUILD_TIMESTAMP` from pipeline start time
2. Formats it in Pacific Time
3. Passes it to the Docker container as an environment variable

The admin page now reads this same environment variable that the main page uses.

## Testing

1. **Session ID:**
   - Open dashboard in two different browsers
   - Check logs - you should see two different session IDs
   - Refresh page - session ID should persist

2. **Build Timestamp:**
   - **In Production (Woodpecker CI):** Build timestamp will show deployment time
   - **In Development:** Shows "Development" with current time
   - Both main page footer and admin page should show the same timestamp

## Notes

- Session IDs are **not** tied to user accounts - they're per-browser-session
- Build timestamp is automatically set by Woodpecker CI - no manual steps needed
- Session ID adds minimal overhead (~1 string concatenation per log)
- The `generate_build_stamp.py` script is no longer needed (kept for reference)
