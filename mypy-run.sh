#!/bin/bash

pip install mypy sqlalchemy-stubs

DIR=$(dirname "$(readlink -f "$0")")

pushd "$DIR" > /dev/null 2>&1
mypy gallery
popd > /dev/null 2>&1
