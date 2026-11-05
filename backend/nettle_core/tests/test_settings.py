import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _import_settings(extra_env):
    env = {key: value for key, value in os.environ.items() if not key.startswith("DJANGO_")}
    env.pop("DATABASE_URL", None)
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", "import nettle_core.settings"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def test_production_settings_refuse_to_start_without_secret_key():
    result = _import_settings({"DJANGO_DEBUG": "0", "DATABASE_URL": "postgres://u:p@db/x"})
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY must be set" in result.stderr


def test_production_settings_refuse_to_start_without_database_url():
    result = _import_settings({"DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": "x" * 50})
    assert result.returncode != 0
    assert "DATABASE_URL must be set" in result.stderr


def test_production_settings_load_when_configured():
    result = _import_settings(
        {"DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": "x" * 50, "DATABASE_URL": "postgres://u:p@db/x"}
    )
    assert result.returncode == 0, result.stderr
