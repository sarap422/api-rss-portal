#!/bin/bash
# uvicornが動いていなければ起動する（複数アプリ対応）

# === rss-portal (port 8001) ===
if ! pgrep -f "uvicorn main:app.*port 8001" > /dev/null; then
    mkdir -p "$HOME/api/rss-portal/logs"
    echo "[$(date)] Starting rss-portal..." >> "$HOME/api/rss-portal/logs/uvicorn.log"
    cd "$HOME/api/rss-portal" || { echo "[$(date)] ERROR: Directory not found" >> "$HOME/api/rss-portal/logs/uvicorn.log"; exit 1; }
    "$HOME/virtualenv/api/rss-portal/3.11/bin/uvicorn" main:app --host 127.0.0.1 --port 8001 >> "$HOME/api/rss-portal/logs/uvicorn.log" 2>&1 &
fi

# === markitdown (port 8002) ===
if ! pgrep -f "uvicorn main:app.*port 8002" > /dev/null; then
    mkdir -p "$HOME/api/markitdown/logs"
    echo "[$(date)] Starting markitdown..." >> "$HOME/api/markitdown/logs/uvicorn.log"
    cd "$HOME/api/markitdown" || { echo "[$(date)] ERROR: Directory not found" >> "$HOME/api/markitdown/logs/uvicorn.log"; exit 1; }
    "$HOME/virtualenv/api/markitdown/3.11/bin/uvicorn" main:app --host 127.0.0.1 --port 8002 >> "$HOME/api/markitdown/logs/uvicorn.log" 2>&1 &
fi
