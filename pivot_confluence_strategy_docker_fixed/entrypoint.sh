#!/usr/bin/env bash
set -e

MODE="${MODE:-backtest}"
CONFIG="${CONFIG:-config.yaml}"
ARGS="--mode ${MODE} --config ${CONFIG}"

if [[ -n "${START}" ]]; then
  ARGS="${ARGS} --start ${START}"
fi
if [[ -n "${END}" ]]; then
  ARGS="${ARGS} --end ${END}"
fi

echo ">> Running: python src/main.py ${ARGS}"
exec python src/main.py ${ARGS}
