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
from packages.platform.autostart import Autostart
from packages.platform.backups import Backups
from packages.platform.runtime import InstanceLock, runtime_paths
from packages.platform.storage import EncryptedStore
from packages.platform.vault import Vault


def serve(
    demo: bool = False,
    port: int = 4173,
    open_browser: bool = True,
    profile: str = "production",
    data_home: str = "",
) -> None:
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("포트는 1024~65535 사이의 정수여야 합니다.")
    logger.remove()
    logger.add(sys.stderr, format="{level}: {message}", diagnose=False, backtrace=False)
    lock = None
    backups = None
    if demo:
        key = Fernet.generate_key()
        store = EncryptedStore(":memory:", lambda: key)
        store.unlock()
        from apps.server.demo import seed

        seed(store)
    else:
        paths = runtime_paths(profile, data_home)
        lock = InstanceLock(paths)
        lock.acquire()
        vault = Vault(paths)
        store = EncryptedStore(paths.database, vault.load_key)
        backups = Backups(store, vault)
    try:
        startup = (
            Autostart(profile, port, data_home)
            if not demo and profile != "test" and sys.platform == "win32"
            else None
        )
        app = create_app(
            store,
            demo=demo,
            port=port,
            profile="demo" if demo else profile,
            backups=backups,
            autostart=startup,
        )
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                access_log=False,
                proxy_headers=False,
                log_level="warning",
            )
        )
        app.state.shutdown = lambda: setattr(server, "should_exit", True)
        if backups:
            backups.start()
        if open_browser:
            url = f"http://127.0.0.1:{port}/#access={app.state.bootstrap}"
            timer = threading.Timer(1.5, webbrowser.open, args=(url,))
            timer.daemon = True
            timer.start()
        logger.info(
            f"Local: http://127.0.0.1:{port} · {'temporary demo' if demo else 'OS key storage'}"
        )
        server.run()
    finally:
        if backups:
            backups.stop()
        store.close()
        if lock:
            lock.release()


if __name__ == "__main__":
    from packages.platform.domain import DomainError

    try:
        fire.Fire(serve)
    except DomainError as error:
        logger.error(str(error))
        raise SystemExit(1) from None
