#!/usr/bin/env bash
# Run the localtuya test suite.
#
# Usage:
#   scripts/run_tests.sh                # full suite
#   scripts/run_tests.sh tests/test_fan.py
#   scripts/run_tests.sh -k fan
#
# Requires the test dependencies first:
#   pip install -r requirements_test.txt
#
# pytest picks up its settings from pyproject.toml ([tool.pytest.ini_options]).
set -euo pipefail

cd "$(dirname "$0")/.."

exec python -m pytest "$@"
