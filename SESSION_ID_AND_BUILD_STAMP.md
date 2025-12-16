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

**Solution:** Build stamp system that tracks git commit, branch, and build date.

**Implementation:**

1. **Build Script** (`generate_build_stamp.py`):
   - Extracts git commit hash (short form)
   - Gets current branch name
   - Records build timestamp
   - Writes to `build_stamp.json`

2. **Admin Page Display**:
   - Shows build info in header: `🏷️ Build: 512fbfe (main) - 2025-12-16 07:26:50 UTC`
   - Falls back to "Development" if no build stamp exists
   - Silently fails if file can't be read

**Build Stamp File Format:**
```json
{
  "commit": "512fbfe",
  "branch": "main",
  "timestamp": "2025-12-16T07:26:50.123456+00:00",
  "build_date": "2025-12-16 07:26:50 UTC"
}
```

**Usage:**
```bash
# Generate build stamp (run during deployment)
python generate_build_stamp.py

# Output:
# Build stamp generated:
#    Commit: 512fbfe
#    Branch: main
#    Date: 2025-12-16 07:26:50 UTC
```

**Benefits:**
- Know exactly which code version is running
- Verify deployments completed successfully
- Track when builds were created
- Debug version-specific issues
- Correlate issues with specific commits

## Files Modified

### Performance Logging with Session ID:
- `web_dashboard/streamlit_app.py` - Added session ID generation and logging
- `web_dashboard/streamlit_utils.py` - Updated `get_user_investment_metrics()` to accept and use session_id
- `PERFORMANCE_LOGGING.md` - Updated documentation with session ID examples

### Build Stamp:
- `generate_build_stamp.py` - New script to generate build stamp
- `build_stamp.json` - Generated build info file (gitignored)
- `web_dashboard/pages/admin.py` - Display build stamp in header

## Integration with CI/CD

Add to your deployment pipeline (e.g., Woodpecker CI):

```yaml
steps:
  - name: generate-build-stamp
    image: python:3.11
    commands:
      - python generate_build_stamp.py
  
  - name: build-docker
    image: docker:latest
    commands:
      - docker build -t myapp:latest .
```

The build stamp will be baked into the Docker image and displayed on the admin page.

## Testing

1. **Session ID:**
   - Open dashboard in two different browsers
   - Check logs - you should see two different session IDs
   - Refresh page - session ID should persist

2. **Build Stamp:**
   - Run `python generate_build_stamp.py`
   - Open admin page
   - Verify build info appears in header
   - Delete `build_stamp.json` and refresh - should show "Development"

## Notes

- Session IDs are **not** tied to user accounts - they're per-browser-session
- Build stamp is **optional** - app works fine without it
- Session ID adds minimal overhead (~1 string concatenation per log)
- Build stamp file should be in `.gitignore` (each deployment generates its own)
