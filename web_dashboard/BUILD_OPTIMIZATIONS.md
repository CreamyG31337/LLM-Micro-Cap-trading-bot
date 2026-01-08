# Build and Deployment Optimizations

This document outlines the optimizations made to ensure fast parallel builds and deployments.

## Build Optimizations

### 1. Parallel Docker Builds

All three Docker images build in parallel:
- `trading-dashboard` (Streamlit)
- `trading-dashboard-flask` (Flask)
- `cookie-refresher` (sidecar)

**Implementation**: Uses background processes (`&`) and `wait` to build all three simultaneously.

```yaml
(docker build -f web_dashboard/Dockerfile -t trading-dashboard:latest . &)
(docker build -f web_dashboard/Dockerfile.flask -t trading-dashboard-flask:latest . &)
(docker build -f web_dashboard/Dockerfile.cookie-refresher -t cookie-refresher:latest . &)
wait  # Wait for all builds to complete
```

### 2. Docker BuildKit

Enabled BuildKit for better caching and parallel layer builds:

```yaml
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

**Benefits**:
- Better layer caching
- Parallel layer builds
- Faster subsequent builds (only changed layers rebuild)

### 3. Optimized Dockerfile Layer Ordering

The `Dockerfile.flask` is optimized for caching:

1. **System dependencies first** (rarely changes)
2. **Requirements.txt copy** (only rebuilds if requirements change)
3. **Dependency installation** (cached unless requirements.txt changes)
4. **Code copy last** (rebuilds on every code change, but dependencies are cached)

This means:
- **First build**: Full build (~2-3 minutes)
- **Code-only changes**: Only code layer rebuilds (~30 seconds)
- **Requirements changes**: Dependencies + code rebuild (~1-2 minutes)

### 4. Optimized Health Checks

Health checks use socket connections instead of HTTP requests:
- **Faster**: Socket check is instant vs HTTP request
- **No auth required**: Doesn't need authentication tokens
- **More reliable**: Works even if Flask hasn't fully initialized routes

## Deployment Optimizations

### 1. Parallel Container Stops

Containers are stopped in parallel:

```bash
(docker stop trading-dashboard || true) &
(docker stop trading-dashboard-flask || true) &
wait
```

### 2. Parallel Container Starts

Streamlit and Flask containers start in parallel:

```bash
# Streamlit starts in background
eval $DOCKER_CMD &
STREAMLIT_PID=$!

# Flask starts immediately after (parallel)
eval $FLASK_CMD

# Wait for Streamlit to finish
wait $STREAMLIT_PID
```

**Time saved**: ~5-10 seconds (containers start simultaneously instead of sequentially)

### 3. Optimized Image Tagging

Image tagging happens after all builds complete (no blocking):

```bash
docker tag trading-dashboard:latest trading-dashboard:${CI_COMMIT_SHA}
docker tag trading-dashboard-flask:latest trading-dashboard-flask:${CI_COMMIT_SHA}
docker tag cookie-refresher:latest cookie-refresher:${CI_COMMIT_SHA}
```

**Note**: Tagging is fast (~1 second), so parallelization isn't needed here.

## Build Time Estimates

### First Build (No Cache)
- **Build time**: ~3-4 minutes (all 3 images in parallel)
- **Deploy time**: ~10-15 seconds
- **Total**: ~3.5-4.5 minutes

### Subsequent Builds (With Cache)

**Code-only changes**:
- **Build time**: ~30-60 seconds (only code layers rebuild)
- **Deploy time**: ~10-15 seconds
- **Total**: ~40-75 seconds

**Requirements changes**:
- **Build time**: ~1.5-2.5 minutes (dependencies + code rebuild)
- **Deploy time**: ~10-15 seconds
- **Total**: ~1.75-2.75 minutes

**No changes** (cache hit):
- **Build time**: ~5-10 seconds (just tagging)
- **Deploy time**: ~10-15 seconds
- **Total**: ~15-25 seconds

## Additional Speed Improvements

### 1. Shared Base Layers

Both `Dockerfile` and `Dockerfile.flask` use:
- Same base image (`python:3.11-slim`)
- Same system dependencies
- Same `uv` installation
- Same requirements.txt

Docker automatically caches these shared layers, so building the second image is faster.

### 2. Incremental File Copying

Static files (Research PDFs) only copy if newer:
```bash
if [ ! -f "$dest_file" ] || [ "$pdf_file" -nt "$dest_file" ]; then
  cp "$pdf_file" "$dest_file"
fi
```

### 3. Efficient Image Cleanup

Old images are cleaned up in parallel:
```bash
docker images -q trading-dashboard | tail -n +6 | xargs -r docker rmi
docker images -q trading-dashboard-flask | tail -n +6 | xargs -r docker rmi
```

## Monitoring Build Performance

To see build times in Woodpecker logs, look for:
- `Building Docker images in parallel...` - Start of builds
- `✅ All images built and tagged` - End of builds
- `✅ All containers deployed successfully` - End of deployment

## Future Optimizations (If Needed)

1. **Multi-stage builds**: Separate build and runtime layers
2. **Docker layer caching**: Use external cache (registry or cache mount)
3. **Build cache mount**: Cache pip/uv downloads between builds
4. **Parallel test execution**: Run tests in parallel if added

## Troubleshooting Slow Builds

If builds are slow:

1. **Check Docker cache**: `docker system df` - ensure cache isn't full
2. **Check disk space**: Low disk space slows Docker
3. **Check network**: Slow network slows package downloads
4. **Check CPU**: High CPU usage slows builds (other processes running?)

To clear cache (if needed):
```bash
docker builder prune -a  # Clears build cache
docker system prune -a   # Clears all unused Docker data
```
