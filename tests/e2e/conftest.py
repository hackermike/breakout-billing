"""Fixtures for Playwright end-to-end tests.

These start a real uvicorn server against a scratch database and drive it with a
browser. They are marked `e2e` and skipped unless Playwright browsers are
installed (CI runs them in a dedicated job).
"""
import os
import socket
import subprocess
import tempfile
import time

import pytest

pytest.importorskip("playwright")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    port = _free_port()
    tmp = tempfile.mkdtemp(prefix="bb-e2e-")
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp}/e2e.db"}
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    subprocess.run(["python", "seed.py"], env=env, cwd=repo_root, check=True)
    proc = subprocess.Popen(
        ["uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        env=env, cwd=repo_root,
    )

    base = f"http://127.0.0.1:{port}"
    try:
        import urllib.request
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{base}/calendar", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("server did not start")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)
