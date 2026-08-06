#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

required_python="3.12"
python_bin="${CAREGIST_PYTHON_BIN:-python3.12}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
  echo "ERROR: Python ${required_python} is required (CI uses ${required_python})." >&2
  exit 1
fi

actual_version="$($python_bin -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$actual_version" != "$required_python" ]]; then
  echo "ERROR: $python_bin is Python $actual_version; expected $required_python." >&2
  exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
  "$python_bin" -m venv .venv
fi

venv_version="$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$venv_version" != "$required_python" ]]; then
  echo "ERROR: existing .venv uses Python $venv_version; move it aside and rerun this command." >&2
  exit 1
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pip check

npm --prefix frontend ci --no-audit --no-fund

echo "CareGist development environment is ready (Python $required_python)."
echo "Backend: .venv/bin/python -m pytest"
echo "Frontend: npm --prefix frontend test"
