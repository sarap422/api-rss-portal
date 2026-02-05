#!/bin/bash
# uvicornが動いていなければ起動する（複数アプリ対応）

# === rss-portal (port 8001) ===
if ! pgrep -f "uvicorn main:app.*port 8001" > /dev/null; then
    echo "[$(date)] Starting rss-portal..." >> /home/[ユーザー名]/api/rss-portal/logs/uvicorn.log
    cd /home/[ユーザー名]/api/rss-portal
    /home/[ユーザー名]/virtualenv/api/rss-portal/3.11/bin/uvicorn main:app --host 127.0.0.1 --port 8001 >> /home/[ユーザー名]/api/rss-portal/logs/uvicorn.log 2>&1 &
fi

# === markitdown (port 8002) ===
if ! pgrep -f "uvicorn main:app.*port 8002" > /dev/null; then
    echo "[$(date)] Starting markitdown..." >> /home/[ユーザー名]/api/markitdown/uvicorn.log
    cd /home/[ユーザー名]/api/markitdown
    /home/[ユーザー名]/virtualenv/api/markitdown/3.11/bin/uvicorn main:app --host 127.0.0.1 --port 8002 >> /home/[ユーザー名]/api/markitdown/uvicorn.log 2>&1 &
fi