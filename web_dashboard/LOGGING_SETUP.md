# Server Logs Setup Guide (Shared Volume Architecture)

This setup ensures that:
1.  **Ollama** writes its logs directly to a shared file (while keeping them visible in Portainer).
2.  **Trading Dashboard** can read that file for the UI.
3.  **Caddy** serves that file so the AI can read it via HTTP.

## 1. Create Host Directory
On your server (`ts-ubuntu-server`), create a dedicated folder for Ollama logs:

```bash
mkdir -p ~/ollama-logs
chmod 777 ~/ollama-logs  # Ensure write permissions for containers
```

## 2. Configure Containers (Portainer)

You need to edit 3 containers.

### A. Ollama Service (The Writer)
Modify your existing Ollama container config:
1.  **Volumes**:
    *   Map Host `~/ollama-logs` -> Container `/var/log/ollama`
2.  **Entrypoint**: Override the default entrypoint to use a shell.
    *   *Portainer -> Command & logging -> Entrypoint*: `/bin/sh`
3.  **Command**: Pipe output to file using `tee` (preserves docker logs + writes to file).
    *   *Portainer -> Command & logging -> Command*: `-c "ollama serve 2>&1 | tee -a /var/log/ollama/server.log"`

### B. Trading Dashboard Service (The Viewer)
1.  **Volumes**:
    *   Map Host `~/ollama-logs` -> Container `/app/web_dashboard/logs/server`
    *   *(Note: This creates a 'server' subfolder inside the app's log dir)*

### C. Caddy Service (The Agent Access)
1.  **Volumes**:
    *   Map Host `~/ollama-logs` -> Container `/srv/logs`

## 3. Verify
1.  **Check File**: On the host, check `tail -f ~/ollama-logs/server.log`. You should see Ollama startup logs.
2.  **Dashboard**: Go to **Admin** -> **System Logs Viewer**. Select "File System" mode. You should see `server/server.log`.
3.  **AI Access**: The AI can now fetch `https://<YOUR_DOMAIN>/logs/server.log`.

## Troubleshooting
*   **"Permission Denied"**: If Ollama crashes instantly, run `chmod 777 ~/ai-trading-logs` on the host again.
*   **No Logs**: Ensure you set the **Entrypoint** to `/bin/sh` and not just the Command.
