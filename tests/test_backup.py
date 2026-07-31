"""Backup and restore round-trip (the scripts themselves)."""
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _make_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute("create table t (x integer)")
    con.execute("insert into t values (42)")
    con.commit()
    con.close()


def _value(path: Path) -> int:
    con = sqlite3.connect(path)
    try:
        return con.execute("select x from t").fetchone()[0]
    finally:
        con.close()


def _run(args, env):
    subprocess.run(args, cwd=ROOT, env=env, check=True, capture_output=True)


@pytest.mark.skipif(not shutil.which("sqlite3"), reason="sqlite3 CLI not available")
def test_backup_and_restore_plaintext(tmp_path):
    db = tmp_path / "src.db"
    _make_db(db)
    dest = tmp_path / "bk"
    env = {**os.environ, "DATABASE_FILE": str(db)}

    _run(["./scripts/backup.sh", str(dest)], env)
    backups = list(dest.glob("breakout-*.db"))
    assert len(backups) == 1

    target = tmp_path / "restored.db"
    _run(["./scripts/restore.sh", str(backups[0]), str(target)], env)
    assert _value(target) == 42


@pytest.mark.skipif(
    not (shutil.which("sqlite3") and shutil.which("openssl")),
    reason="sqlite3/openssl not available",
)
def test_backup_and_restore_encrypted(tmp_path):
    db = tmp_path / "src.db"
    _make_db(db)
    dest = tmp_path / "bk"
    env = {**os.environ, "DATABASE_FILE": str(db), "BACKUP_PASSPHRASE": "drill-pw"}

    _run(["./scripts/backup.sh", str(dest)], env)
    encrypted = list(dest.glob("breakout-*.db.enc"))
    assert len(encrypted) == 1
    assert not list(dest.glob("breakout-*.db"))  # no plaintext left behind

    target = tmp_path / "restored.db"
    _run(["./scripts/restore.sh", str(encrypted[0]), str(target)], env)
    assert _value(target) == 42
