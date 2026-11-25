#!/usr/bin/env bash
# Rebuild public/ from the live Wix site. Needs network access to lynxware.org and the Wix CDNs,
# Playwright (Chromium) and Python 3. Hand-written files (site.css, site.js, 404.html, fonts/, _files/) are kept.
set -euo pipefail
cd "$(dirname "$0")/.."
CAP=${CAPTURE_DIR:-$(mktemp -d)}
node tools/capture.cjs "$CAP" $(cat tools/pages.txt)
rm -rf public/assets public/m
python3 -I tools/convert.py "$CAP" public tools/videos.txt
python3 -I tools/build_config.py
