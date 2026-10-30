"""Shared test setup: point the index at a scratch database before any test module imports it."""

import os

os.environ.setdefault("INDEX_DB", "/tmp/media-index-test.db")
