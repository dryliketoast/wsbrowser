#!/usr/bin/env bash
# Build a single-file wsbrowser executable with PyInstaller.
#
# Output: dist/wsbrowser-<version>-<os>-<arch>, plus a dist/wsbrowser copy.
# The binary bundles its own Python, so the target machine needs neither
# Python nor uv. It only runs on the OS/arch it was built on (and needs a
# glibc no older than the build host's), so build on each target platform.
set -euo pipefail

cd "$(dirname "$0")/.."

version=$(uv run --no-sync python -c 'import wsbrowser; print(wsbrowser.__version__)')
os=$(uname -s | tr '[:upper:]' '[:lower:]')
arch=$(uname -m)
name="wsbrowser-${version}-${os}-${arch}"

echo "==> Syncing build environment"
uv sync --group build

echo "==> Running tests"
uv run pytest -q

echo "==> Building ${name}"
uv run pyinstaller \
    --onefile \
    --clean \
    --noconfirm \
    --name "$name" \
    --distpath dist \
    --workpath build/pyinstaller \
    --specpath build \
    --collect-data textual \
    wsbrowser/__main__.py

cp "dist/${name}" dist/wsbrowser

echo "==> Smoke test"
dist/wsbrowser --help >/dev/null

echo
echo "Built: dist/${name} ($(du -h "dist/${name}" | cut -f1))"
echo "Copy:  dist/wsbrowser"
