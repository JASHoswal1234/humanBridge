"""Keep collection-time SQLite initialization and test uploads out of the demo database."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory

_storage = TemporaryDirectory(prefix='humanbridge-pytest-', ignore_cleanup_errors=True)
os.environ['DB_PATH'] = str(Path(_storage.name) / 'test.db')
os.environ['UPLOAD_DIR'] = str(Path(_storage.name) / 'uploads')
