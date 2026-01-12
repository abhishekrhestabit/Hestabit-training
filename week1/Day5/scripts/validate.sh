#!/usr/bin/env bash

LOG_DIR="logs"
LOG_FILE="$LOG_DIR/validate.log"

mkdir -p "$LOG_DIR"

timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  echo "[$(timestamp)] $1" | tee -a "$LOG_FILE"
}

log "Running validation..."

# Check src/
if [ ! -d "src" ]; then
  log "ERROR: src/ directory missing"
  exit 1
fi

# Check config.json
if [ ! -f "config.json" ]; then
  log "ERROR: config.json missing"
  exit 1
fi

# Validate JSON
if ! jq empty config.json >/dev/null 2>&1; then
  log "ERROR: Invalid JSON in config.json"
  exit 1
fi

log "Validation successful"
