#!/bin/bash

# major.minor.patch.preminor|prepatch
RELEASE_TYPE=$1

poetry version $1
NEW_VERSION=$(poetry version | grep -Eo "[0-9]\.[0-9]\.[0-9].?+")
git add pyproject.toml
git commit -m "bump version"
git tag -ma "$NEW_VERSION"

