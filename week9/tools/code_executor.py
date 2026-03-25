import re
import subprocess
import sys
import tempfile
import os
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAFE_DIR = PROJECT_ROOT / "workspace"
SAFE_DIR.mkdir(parents=True, exist_ok=True)

IMPORT_TO_PIP = {
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
}

def _extract_imports(code: str) -> list[str]:
    pattern = re.compile(r'^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)', re.MULTILINE)
    seen = []
    for m in pattern.finditer(code):
        pkg = m.group(1)
        if pkg not in seen:
            seen.append(pkg)
    return seen

def auto_install_missing(code: str) -> list[str]:
    installed = []
    for import_name in _extract_imports(code):
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
            err = (result.stderr or result.stdout or "unknown").strip()
            print(f"   Failed to install {pip_name}: {err[:120]}", flush=True)

    return installed

def execute_python_code(code: str, timeout: int = 60) -> dict:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(textwrap.dedent(code))
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            cwd=PROJECT_ROOT,   # Keep ./workspace/... paths aligned with validator/logs
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "error": None if result.returncode == 0 else result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": f"Timed out after {timeout}s.",
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": str(e),
        }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
