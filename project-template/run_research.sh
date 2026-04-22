#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO/.venv/bin/python"
TODAY=$(date +%Y%m%d)
LOG_DIR="$REPO/logs"
STEP="${1:-status}"

log_ok()   { echo "✓ $1"; }
log_err()  { echo "✗ $1"; }
log_info() { echo "→ $1"; }
log_warn() { echo "⚠ $1"; }

preflight() {
  [ -f "$REPO/config.yaml" ] || { log_err "config.yaml tidak ditemukan"; exit 1; }

  [ -f "$REPO/.env" ] || { log_err ".env tidak ditemukan (TELEGRAM_CHAT_ID wajib di project .env)"; exit 1; }
  if ! grep -q '^TELEGRAM_CHAT_ID=' "$REPO/.env"; then
    log_err "TELEGRAM_CHAT_ID tidak ditemukan di project .env"
    exit 1
  fi

  [ -f "$HOME/.hermes/.env" ] || { log_err "~/.hermes/.env tidak ditemukan"; exit 1; }
  if ! grep -q '^TELEGRAM_BOT_TOKEN=' "$HOME/.hermes/.env"; then
    log_err "TELEGRAM_BOT_TOKEN tidak ditemukan di ~/.hermes/.env"
    exit 1
  fi
  if ! grep -q '^JINA_API_KEY=' "$HOME/.hermes/.env"; then
    log_err "JINA_API_KEY tidak ditemukan di ~/.hermes/.env"
    exit 1
  fi

  mkdir -p "$LOG_DIR" \
           "$REPO/queue/pending" "$REPO/queue/active" "$REPO/queue/done" "$REPO/queue/failed" "$REPO/queue/dead" \
           "$REPO/vault/sources" "$REPO/vault/extracted" "$REPO/vault/synthesis" "$REPO/vault/output" "$REPO/vault/memory"

  log_ok "Preflight check lulus"
}

register_cron() {
  local CRON_NOTIFY="*/5 * * * * cd $REPO && $VENV orchestrator/notify.py --summary >> $LOG_DIR/notify.log 2>&1"
  local CRON_WATCHDOG="*/2 * * * * cd $REPO && $VENV orchestrator/watchdog.py >> $LOG_DIR/watchdog.log 2>&1"
  local CRON_INDEXER="0 * * * * cd $REPO && $VENV scripts/indexer.py --rebuild >> $LOG_DIR/indexer.log 2>&1"

  (crontab -l 2>/dev/null | grep -v "$REPO" || true; echo "$CRON_NOTIFY"; echo "$CRON_WATCHDOG"; echo "$CRON_INDEXER") | crontab -
  log_ok "Cron jobs terdaftar (idempotent by repo-path filter)"
}

step_setup() {
  preflight
  register_cron
}

step_status() {
  preflight
  local pending=$(ls "$REPO/queue/pending" 2>/dev/null | wc -l | tr -d ' ')
  local active=$(ls "$REPO/queue/active" 2>/dev/null | wc -l | tr -d ' ')
  local done=$(ls "$REPO/queue/done" 2>/dev/null | wc -l | tr -d ' ')
  local failed=$(ls "$REPO/queue/failed" 2>/dev/null | wc -l | tr -d ' ')
  local dead=$(ls "$REPO/queue/dead" 2>/dev/null | wc -l | tr -d ' ')

  log_info "Queue status"
  echo "Pending: $pending"
  echo "Active : $active"
  echo "Done   : $done"
  echo "Failed : $failed"
  echo "Dead   : $dead"
}

case "$STEP" in
  setup)
    step_setup
    ;;
  status)
    step_status
    ;;
  *)
    log_warn "Step '$STEP' belum diimplementasikan pada scaffold Phase 2"
    step_status
    ;;
esac

log_info "Selesai: $STEP"
