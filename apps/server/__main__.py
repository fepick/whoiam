"""python -m apps.server --demo=True 로 가상 데이터 실행."""

import sys
import threading
import webbrowser
from pathlib import Path

import fire
import uvicorn
from cryptography.fernet import Fernet
from loguru import logger

from apps.server.api import create_app
from packages.platform.keys import os_key
from packages.platform.storage import EncryptedStore

#: 운영 DB 경로는 소스 트리의 로컬 전용 경계로 고정한다.
DATABASE_PATH = (
    Path(__file__).resolve().parents[2] / ".private" / "database" / "whoiam.sqlite3"
)


def serve(demo: bool = False, port: int = 4173, open_browser: bool = True) -> None:
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("포트는 1024~65535 사이의 정수여야 합니다.")
    logger.remove()
    logger.add(sys.stderr, format="{level}: {message}", diagnose=False, backtrace=False)
    if demo:
        key = Fernet.generate_key()
        store = EncryptedStore(":memory:", lambda: key)
        store.unlock()
        from apps.server.demo import seed

        seed(store)
    else:
        store = EncryptedStore(DATABASE_PATH, lambda: os_key(DATABASE_PATH))
    try:
        app = create_app(store, demo=demo, port=port)
        if open_browser:
            url = f"http://127.0.0.1:{port}/#access={app.state.bootstrap}"
            timer = threading.Timer(1.5, webbrowser.open, args=(url,))
            timer.daemon = True
            timer.start()
        logger.info(
            f"Local: http://127.0.0.1:{port} · {'temporary demo' if demo else 'OS key storage'}"
        )
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            access_log=False,
            proxy_headers=False,
            log_level="warning",
        )
    finally:
        store.close()


if __name__ == "__main__":
    fire.Fire(serve)
