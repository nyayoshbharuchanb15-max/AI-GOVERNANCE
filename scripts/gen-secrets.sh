#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  gen-secrets.sh — emit a production-ready .env with fresh secrets
# ═══════════════════════════════════════════════════════════════════
#
# Reads .env.example from the repo root and replaces every __GENERATE__
# placeholder with a 32-byte URL-safe random token. Writes the result to
# stdout — pipe to a file with:
#
#     bash scripts/gen-secrets.sh > .env
#     chmod 600 .env
#
# The orchestrator's startup validator (orchestrator/config.py) refuses
# to boot if any GOV_* secret is unset, matches a known-weak value, or
# is shorter than 24 characters. This script produces 32-byte
# (>192-bit) secrets by default.
#
# Idempotency: running twice produces two different .env files with
# independent secrets. Do NOT run it against an already-live .env
# (secrets change and every issued session breaks).
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="${ROOT_DIR}/.env.example"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "gen-secrets.sh: cannot find $TEMPLATE" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "gen-secrets.sh: python3 is required for secret generation" >&2
  exit 1
fi

gen() { python3 -c 'import secrets; print(secrets.token_urlsafe(32))'; }

# Rewrite each `KEY=__GENERATE__` line (start of line, after the `=`, no
# quotes) with a fresh 32-byte URL-safe token. The `__GENERATE__` string
# appearing anywhere else in the file (e.g. documentation blocks) is left
# untouched.
python3 - "$TEMPLATE" <<'PY'
import re, secrets, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    text = f.read()

pattern = re.compile(r"^([A-Z][A-Z0-9_]*=)__GENERATE__$", re.MULTILINE)
out = pattern.sub(lambda m: m.group(1) + secrets.token_urlsafe(32), text)
sys.stdout.write(out)
PY
