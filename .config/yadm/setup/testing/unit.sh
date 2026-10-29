#!/bin/sh
# Run the setup/ unittest suite under the oldest and newest supported Pythons, read-only.
set -eu
TESTING=$(cd "$(dirname "$0")" && pwd)
. "$TESTING/lib.sh"
SETUP=$(dirname "$TESTING")

suite() {
  docker run --rm --volume "$SETUP:/setup:ro" --workdir /setup "python:$1-slim" \
    python3 -m unittest discover -v
}

for version in 3.9 3.14; do
  check "unittest under python:$version-slim" suite "$version"
done
finish
