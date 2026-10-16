#!/bin/bash

# Confirm that a deployed environment is serving the version you think it is.
#
# Usage: ./scripts/check_deployed_version.sh <base-url> [expected-version]
# Example: ./scripts/check_deployed_version.sh https://dados.gov.pt 16.0.0.12
#          ./scripts/check_deployed_version.sh https://dados.gov.pt
#
# Without an expected version, the script reports what the environment serves
# and compares it against the newest tag in backend/. With one, it fails when
# they differ.
#
# Why this exists: the backend reports the version of the *installed package*,
# read through importlib metadata -- not the number sitting in pyproject.toml.
# A deploy that ships new code without reinstalling the package, or that reuses
# a cached image, keeps answering with the previous version, and the portal
# footer repeats it to every visitor. That is exactly how the footer came to
# announce udata 15.0.0 for months. This check puts the discrepancy in front of
# whoever ran the deploy instead.

set -e

BASE_URL="${1%/}"
EXPECTED="$2"

if [ -z "$BASE_URL" ]; then
    echo "Usage: $0 <base-url> [expected-version]"
    echo "Example: $0 https://dados.gov.pt 16.0.0.12"
    exit 1
fi

SITE_JSON=$(curl -fsS --max-time 20 "$BASE_URL/api/1/site/" 2>/dev/null) || {
    echo "Error: could not read $BASE_URL/api/1/site/"
    exit 1
}

SERVED=$(printf '%s' "$SITE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version") or "")' 2>/dev/null || true)

if [ -z "$SERVED" ]; then
    echo "Error: $BASE_URL/api/1/site/ answered without a 'version' field"
    exit 1
fi

if [ -z "$EXPECTED" ]; then
    REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)/backend"
    EXPECTED=$(git -C "$REPO_DIR" tag --list 'v*' --sort=-v:refname | head -1 | sed 's/^v//')
    if [ -n "$EXPECTED" ]; then
        echo "No expected version given; comparing against the newest tag in backend/: $EXPECTED"
    fi
fi

echo "$BASE_URL serves udata $SERVED"

if [ -z "$EXPECTED" ]; then
    echo "Nothing to compare against — pass an expected version to make this a check."
    exit 0
fi

if [ "$SERVED" != "$EXPECTED" ]; then
    echo ""
    echo "MISMATCH: expected $EXPECTED, environment serves $SERVED"
    echo "The code may be deployed without the package being reinstalled: the version"
    echo "comes from the installed distribution metadata, not from pyproject.toml."
    echo "Rebuild the image (or re-run the install step) and check again."
    exit 1
fi

echo "OK: matches the expected version."
