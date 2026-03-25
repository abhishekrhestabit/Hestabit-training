"""
tools/code_executor.py
─────────────────────────────────────────────────────────────────
Python code execution utilities for the pipeline.

Used directly by day3_pipeline.py — not via AutoGen agents.

Public API (what the pipeline calls):
    auto_install_missing(code)        → list[str]  (installs packages)
    execute_python_code(code, timeout)→ dict       (runs code, returns result)

The pipeline calls these two in sequence:
    auto_install_missing(code)   # install anything missing first
    result = execute_python_code(code)   # then run
─────────────────────────────────────────────────────────────────
"""

import re
import subprocess
import sys
import tempfile
import os
import textwrap


# ─────────────────────────────────────────
#  Import → pip package name mapping
#  Some packages have different import vs install names
# ─────────────────────────────────────────

IMPORT_TO_PIP = {
    "sklearn":  "scikit-learn",
    "cv2":      "opencv-python",
    "PIL":      "Pillow",
    "bs4":      "beautifulsoup4",
    "yaml":     "pyyaml",
    "dotenv":   "python-dotenv",
    "dateutil": "python-dateutil",
}


def _extract_imports(code: str) -> list[str]:
    """Return all top-level package names imported in the code."""
    pattern = re.compile(
        r'^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)', re.MULTILINE
    )
    seen = []
    for m in pattern.finditer(code):
        pkg = m.group(1)
        if pkg not in seen:
            seen.append(pkg)
    return seen


# ─────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────

def auto_install_missing(code: str) -> list[str]:
    """
    Scan code for imports and pip-install any that are missing.

    Uses the venv's own pip (sys.executable → venv python → venv pip).
    No --break-system-packages needed inside a venv.

    Returns list of package names that were installed.
    Prints progress to stdout for pipeline CLI display.
    """
    installed = []
    for import_name in _extract_imports(code):
        # Try importing — if it works, nothing to do
        try:
            __import__(import_name)
            continue
        except ImportError:
            pass

        pip_name = IMPORT_TO_PIP.get(import_name, import_name)
        print(f"   Installing: {pip_name} ...", flush=True)

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pip_name, "-q"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"   Installed: {pip_name}", flush=True)
            installed.append(pip_name)
        else:
            err = (result.stderr or result.stdout or "unknown error").strip()
            print(f"   Failed to install {pip_name}: {err[:120]}", flush=True)

    return installed


def execute_python_code(code: str, timeout: int = 60) -> dict:
    """
    Execute a Python code string in an isolated subprocess.

    Returns:
        {
            "success": bool,
            "stdout":  str,   — everything printed via print()
            "stderr":  str,   — tracebacks / warnings
            "error":   str | None,  — None on success, error message on failure
        }
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(textwrap.dedent(code))
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "stdout":  result.stdout.strip(),
            "stderr":  result.stderr.strip(),
            "error":   None if result.returncode == 0 else result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout":  "",
            "stderr":  "",
            "error":   f"Timed out after {timeout}s.",
        }
    except Exception as e:
        return {
            "success": False,
            "stdout":  "",
            "stderr":  "",
            "error":   str(e),
        }
    finally:
        os.unlink(tmp_path)