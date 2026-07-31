"""Tests for the dry-run CLI mode."""

import subprocess
import sys
from pathlib import Path


def test_dry_run_produces_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "--dry-run"],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "Total cases" in result.stdout
    assert "Per-Layer" in result.stdout
    assert "Attribution" in result.stdout