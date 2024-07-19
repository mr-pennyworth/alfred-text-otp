#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Print commands and their arguments as they are executed.
set -x

NAME="alfred-text-otp"
ZIP_FOLDER_NAME="$NAME-main"
REPO="https://github.com/mr-pennyworth/$NAME"
WORKFLOW_ZIP="$REPO/archive/refs/heads/main.zip"

# Download the workflow code
curl -sL "$WORKFLOW_ZIP" -o "/tmp/$NAME.zip"

# Unzip the workflow code
if [ -d "/tmp/$ZIP_FOLDER_NAME" ]; then
  rm -r "/tmp/$ZIP_FOLDER_NAME"
fi
unzip -q "/tmp/$NAME.zip" -d "/tmp"

# Package the workflow
cd "/tmp/$ZIP_FOLDER_NAME"
zip -qr "$NAME.alfredworkflow" *

# Install the workflow
open "$NAME.alfredworkflow"
