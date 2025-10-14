#!/bin/bash
set -e

rm -rf ../dist/*

echo "Building 2FA-code-catcher..."
pyinstaller \
  --onefile \
  --name 2FA-code-catcher \
  --distpath ../dist \
  --workpath ../build \
  --specpath ../ \
  ../src/2FA-code-catcher.py


echo "✅ Build complete. Executable is ../dist/2FA-code-catcher"