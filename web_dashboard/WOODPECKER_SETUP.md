# Woodpecker CI/CD Setup Guide

## Overview

Woodpecker will build the Docker image for the Streamlit dashboard. You'll use Portainer to manage the container deployment.

## Step 1: Add Repository to Woodpecker

1. Open your Woodpecker dashboard
2. Go to **Repositories**
3. Click **"Add Repository"** or sync repositories
4. Find and activate your `LLM-Micro-Cap-trading-bot` repository

## Step 2: Configure Secrets/Environment Variables

In Woodpecker, go to your repository → **Settings** → **Secrets**, and add:

### Required Secrets:
- **`SUPABASE_URL`** - Your Supabase project URL (e.g., `https://xxxxx.supabase.co`)
- **`SUPABASE_PUBLISHABLE_KEY`** - Your Supabase publishable key (for user authentication)
- **`SUPABASE_SECRET_KEY`** - Your Supabase service role key (for admin scripts and debug operations)

### Optional Secrets (if using Docker registry):
- **`DOCKER_USERNAME`** - Docker Hub/registry username
- **`DOCKER_PASSWORD`** - Docker Hub/registry password

### Optional Secrets (if using SSH deploy instead of Portainer):
- **`SSH_USER`** - SSH username for server
- **`SSH_HOST`** - Server hostname/IP
- **`SSH_KEY`** - SSH private key (if using key auth)

## Step 3: Verify Docker Socket Access

Woodpecker needs access to the Docker socket to build images. Ensure:
- Woodpecker agent has `/var/run/docker.sock` mounted
- The agent user has permission to use Docker

## Step 4: Workflow

1. **Push to repository** → Woodpecker builds the image
2. **Image is available** locally on the server (or in registry if you push)
3. **In Portainer**:
   - Go to **Images** → find `trading-dashboard:latest`
   - Create/update container with environment variables:
     - `SUPABASE_URL`
     - `SUPABASE_PUBLISHABLE_KEY` (for user authentication)
     - `SUPABASE_SECRET_KEY` (for admin scripts)
     - `STREAMLIT_SERVER_HEADLESS=true`
     - `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`
   - Map port `8501`
   - Set restart policy to `unless-stopped`

## Simplified Pipeline (Build Only)

Since you're using Portainer for container management, the `.woodpecker.yml` can be simplified to just build the image. The current config includes a deploy step that uses SSH - you can remove that if you're only using Portainer.

## Environment Variables in Portainer

When creating the container in Portainer, set these environment variables:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
SUPABASE_SECRET_KEY=your-secret-key
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

**Note:** `SUPABASE_SECRET_KEY` is required for admin scripts and debug operations. It's safe to include in the container since it's server-side only and never exposed to users.

## Troubleshooting

### Build Fails
- Check Woodpecker logs for errors
- Verify Docker socket is accessible
- Ensure build context is correct (project root)

### Image Not Appearing in Portainer
- Check if Woodpecker and Portainer are on the same server
- Verify image was built successfully
- Check Docker images: `docker images | grep trading-dashboard`

### Container Can't Connect to Supabase
- Verify environment variables are set correctly in Portainer
- Check Supabase URL and key are correct
- Ensure network connectivity from container to Supabase

