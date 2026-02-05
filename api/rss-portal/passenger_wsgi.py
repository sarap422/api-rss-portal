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

# プロジェクトディレクトリをパスに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# 環境変数設定（本番環境では .env から読み込むか、cPanelで設定）
# os.environ.setdefault('GEMINI_API_KEY', 'your-api-key-here')

# uvicornプロセスを管理
UVICORN_PID_FILE = os.path.join(SCRIPT_DIR, 'data', 'uvicorn.pid')
UVICORN_PORT = 8001


def is_uvicorn_running():
    """uvicornが起動中かチェック"""
    if not os.path.exists(UVICORN_PID_FILE):
        return False
    
    try:
        with open(UVICORN_PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # プロセスが存在するかチェック
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def start_uvicorn():
    """uvicornをバックグラウンドで起動"""
    if is_uvicorn_running():
        return
    
    # data ディレクトリを作成
    os.makedirs(os.path.dirname(UVICORN_PID_FILE), exist_ok=True)
    
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    # PIDを保存
    with open(UVICORN_PID_FILE, 'w') as f:
        f.write(str(process.pid))
    
    # 起動を待つ
    time.sleep(2)


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
