#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
echo "Pre-commit hook installed via core.hooksPath = .githooks"
echo "Bypass for emergencies: git commit --no-verify"
