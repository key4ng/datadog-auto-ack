#!/bin/sh
set -eu

MARKER="codex-datadog-auto-ack"
tmp="$(mktemp)"
crontab -l 2>/dev/null | grep -v "# $MARKER" > "$tmp" || true
crontab "$tmp"
rm "$tmp"

printf "Removed cron lines tagged %s\n" "$MARKER"
