"""
Passenger WSGI Entry Point for ColorfulBox
LiteSpeed + Passenger → uvicorn → FastAPI の構成

Note: PassengerはASGIを直接サポートしないため、
uvicornをサブプロセスとして起動する方式を使用
"""

import os
import sys
import subprocess
import time
import signal
import fcntl
import socket

# プロジェクトディレクトリをパスに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# uvicornプロセスを管理
UVICORN_PID_FILE = os.path.join(SCRIPT_DIR, 'data', 'uvicorn.pid')
UVICORN_LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
UVICORN_PORT = 8001


def is_uvicorn_running():
    """uvicornが起動中かチェック（PID + プロセス名検証 + ポート接続チェック）"""
    if not os.path.exists(UVICORN_PID_FILE):
        return False

    try:
        with open(UVICORN_PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        # プロセスが存在するかチェック
        os.kill(pid, 0)

        # /proc/{pid}/cmdline でuvicornプロセスか検証（Linux）
        try:
            with open(f'/proc/{pid}/cmdline', 'r') as f:
                cmdline = f.read()
                if 'uvicorn' not in cmdline:
                    return False
        except (IOError, PermissionError):
            # /proc が利用できない環境ではポート接続チェックにフォールバック
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', UVICORN_PORT))
                sock.close()
                if result != 0:
                    return False
            except (socket.error, OSError):
                return False

        return True
    except (OSError, ValueError):
        return False


def start_uvicorn():
    """uvicornをバックグラウンドで起動（ファイルロックでTOCTOU防止）"""
    # data ディレクトリを作成
    os.makedirs(os.path.dirname(UVICORN_PID_FILE), exist_ok=True)
    os.makedirs(UVICORN_LOG_DIR, exist_ok=True)

    lock_file = UVICORN_PID_FILE + '.lock'
    try:
        lock_fd = open(lock_file, 'w')
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            # 別のプロセスが起動中 → スキップ
            lock_fd.close()
            return

        # ロック取得後に再チェック
        if is_uvicorn_running():
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            return

        # ログファイルを開く
        stdout_log = open(os.path.join(UVICORN_LOG_DIR, 'uvicorn_stdout.log'), 'a')
        stderr_log = open(os.path.join(UVICORN_LOG_DIR, 'uvicorn_stderr.log'), 'a')

        # uvicornをサブプロセスとして起動
        process = subprocess.Popen(
            [
                sys.executable, '-m', 'uvicorn',
                'main:app',
                '--host', '127.0.0.1',
                '--port', str(UVICORN_PORT),
                '--workers', '1',
            ],
            cwd=SCRIPT_DIR,
            stdout=stdout_log,
            stderr=stderr_log,
            start_new_session=True
        )

        # PIDを保存
        with open(UVICORN_PID_FILE, 'w') as f:
            f.write(str(process.pid))

        # ロック解放
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

        # 起動を待つ
        time.sleep(2)

    except Exception:
        try:
            lock_fd.close()
        except Exception:
            pass


def application(environ, start_response):
    """
    WSGIアプリケーション
    実際のリクエストはuvicornにプロキシされるため、
    これはフォールバック用
    """
    # uvicornが起動していなければ起動
    start_uvicorn()

    status = '200 OK'
    output = b'RSS Portal API is running. Please configure proxy to port 8001.'

    response_headers = [
        ('Content-type', 'text/plain'),
        ('Content-Length', str(len(output)))
    ]

    start_response(status, response_headers)
    return [output]


# Passengerが呼び出すアプリケーション
if __name__ != '__main__':
    start_uvicorn()
