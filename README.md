# datadog-auto-ack

For when your wife/girlfriend's company uses Datadog, write access to API keys is disabled, and someone configured 100+ stupid/noisy SMS alerts that mostly just need an ack.

This repo contains a small Codex skill and local macOS scripts that watch Datadog-style SMS/iMessage alerts and automatically reply with the number before `ack` or `ack all`.

Examples:

- `Reply 1 ack, 2 escalate, 3 resolve` -> replies `1`
- `Reply 11 ack all, 12 escalate all, 13 resolve all` -> replies `11`
- `Reply 101 ack all, 102 escalate all, 103 resolve all` -> replies `101`

## Safety model

- Local-only: reads `~/Library/Messages/chat.db` and sends via macOS Messages.
- No Datadog API key required.
- No Datadog write access required.
- Tracks processed message IDs so it does not reply twice.
- Logs message IDs and chosen replies, not alert bodies.

macOS Full Disk Access is required for the scheduler process because Messages data is privacy-protected.

## Install

```bash
cd skills/datadog-auto-ack
AUTO_ACK_TARGET=43152 scripts/install_cron.sh
```

Then grant Full Disk Access to:

- `/usr/sbin/cron`
- the Python executable printed by the installer

## Verify

```bash
crontab -l | grep codex-datadog-auto-ack
cat ~/.codex/datadog-auto-ack/heartbeat.txt
tail -n 50 ~/.codex/datadog-auto-ack/auto_ack.log
tail -n 50 ~/.codex/datadog-auto-ack/cron.err
```

## Uninstall

```bash
cd skills/datadog-auto-ack
scripts/uninstall_cron.sh
```
