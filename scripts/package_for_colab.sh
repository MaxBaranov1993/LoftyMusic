#!/bin/bash
# Package the lofty worker source code for upload to Google Colab.
# Creates lofty-source.zip with only the files needed by the worker.

set -e
cd "$(dirname "$0")/.."

echo "Packaging lofty worker for Colab..."

# Create a clean temp directory
rm -rf /tmp/lofty-colab-package
mkdir -p /tmp/lofty-colab-package/lofty

# Copy only what the worker needs
cp pyproject.toml /tmp/lofty-colab-package/lofty/
cp -r src /tmp/lofty-colab-package/lofty/

# Create the zip
cd /tmp/lofty-colab-package
zip -qr lofty-source.zip lofty/

# Move to project root
mv lofty-source.zip "$(dirname "$0")/../lofty-source.zip"

# Cleanup
rm -rf /tmp/lofty-colab-package

echo "Created lofty-source.zip ($(du -h "$(dirname "$0")/../lofty-source.zip" | cut -f1))"
echo "Upload this file to Google Colab in Step 3b."
