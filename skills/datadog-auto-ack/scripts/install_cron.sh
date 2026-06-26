#!/bin/sh
set -eu

RUNTIME_DIR="${AUTO_ACK_RUNTIME_DIR:-$HOME/.codex/datadog-auto-ack}"
TARGET="${AUTO_ACK_TARGET:-43152}"
PYTHON_BIN="${AUTO_ACK_PYTHON:-$(command -v python3)}"
SOURCE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MARKER="codex-datadog-auto-ack"

mkdir -p "$RUNTIME_DIR"
cp "$SOURCE_DIR/imessage_auto_ack.py" "$RUNTIME_DIR/imessage_auto_ack.py"
chmod +x "$RUNTIME_DIR/imessage_auto_ack.py"

cat > "$RUNTIME_DIR/run.sh" <<EOF
#!/bin/sh
set -eu

BASE="$RUNTIME_DIR"
LOCK_DIR="/tmp/datadog_auto_ack.lock"

if ! mkdir "\$LOCK_DIR" 2>/dev/null; then
  exit 0
fi

cleanup() {
  rmdir "\$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

AUTO_ACK_RUNTIME_DIR="\$BASE" \\
AUTO_ACK_TARGET="$TARGET" \\
AUTO_ACK_STATE="\$BASE/state.json" \\
AUTO_ACK_LOG="\$BASE/auto_ack.log" \\
AUTO_ACK_HEARTBEAT="\$BASE/heartbeat.txt" \\
"$PYTHON_BIN" "\$BASE/imessage_auto_ack.py" --once >>"\$BASE/cron.out" 2>>"\$BASE/cron.err"
EOF

chmod +x "$RUNTIME_DIR/run.sh"

tmp="$(mktemp)"
crontab -l 2>/dev/null | grep -v "# $MARKER" > "$tmp" || true
printf "%s\n" "* * * * * $RUNTIME_DIR/run.sh # $MARKER" >> "$tmp"
crontab "$tmp"
rm "$tmp"

printf "Installed Datadog auto-ack cron job for target %s\n" "$TARGET"
printf "Runtime directory: %s\n" "$RUNTIME_DIR"
printf "If it cannot read Messages, grant Full Disk Access to /usr/sbin/cron and %s\n" "$PYTHON_BIN"
