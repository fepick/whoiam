from pathlib import Path
from typing import Iterator

import pytest
from cryptography.fernet import Fernet

from packages.platform.storage import EncryptedStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[EncryptedStore]:
    key = Fernet.generate_key()
    database = EncryptedStore(tmp_path / "synthetic.sqlite3", lambda: key)
    database.unlock()
    yield database
    database.close()
