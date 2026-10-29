#!/bin/sh
# Run the setup/ unittest suite under the oldest and newest supported Pythons, read-only.
set -eu
TESTING=$(cd "$(dirname "$0")" && pwd)
. "$TESTING/lib.sh"
SETUP=$(dirname "$TESTING")

image() {
  docker build --quiet --build-arg "PYTHON=$1" --tag "converge-unit:$1" \
    --file "$TESTING/Dockerfile.unit" "$TESTING" > /dev/null
}

suite() {
  docker run --rm --volume "$SETUP:/setup:ro" --workdir /setup "converge-unit:$1" \
    python3 -m unittest discover -v
}

for version in 3.9 3.14; do
  check "image converge-unit:$version (python:$version-slim + git)" image "$version"
  check "unittest under python:$version-slim" suite "$version"
done
finish
