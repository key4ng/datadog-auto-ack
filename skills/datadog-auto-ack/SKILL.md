---
name: datadog-auto-ack
description: Set up, inspect, debug, or uninstall a local macOS iMessage/SMS auto-ack monitor for Datadog alert texts. Use when the user wants Codex to auto-reply to Datadog SMS alerts by sending the number before "ack" or "ack all", configure a cron-based monitor, check Full Disk Access issues for Messages, or troubleshoot the local auto-ack state/logs.
---

# Datadog Auto Ack

## Overview

Install a local macOS cron monitor that reads the Messages SQLite database read-only, watches one alert sender, and replies through the Messages app with the number immediately before `ack` or `ack all`.

The monitor is intentionally narrow:

- It watches one sender or short code, default `43152`.
- It only acts on incoming messages that contain a `Reply ... <number> ack` or `Reply ... <number> ack all` option list.
- It records processed message row IDs in a state file so it does not reply twice.
- It never uses Datadog API keys and does not require write access to Datadog.

## Install

Use `scripts/install_cron.sh` from this skill. It copies `scripts/imessage_auto_ack.py` into `~/.codex/datadog-auto-ack`, writes a cron wrapper, and installs one crontab line tagged `codex-datadog-auto-ack`.

Typical install:

```bash
scripts/install_cron.sh
```

Install for a different sender:

```bash
AUTO_ACK_TARGET=12345 scripts/install_cron.sh
```

After install, macOS may require Full Disk Access for:

- `/usr/sbin/cron`
- The Python executable used by the wrapper, usually `python3` or a resolved version such as `/opt/homebrew/anaconda3/bin/python3.12`

Full Disk Access is needed because the monitor reads `~/Library/Messages/chat.db`. The user must grant this manually in System Settings.

## Verify

Check the installed crontab:

```bash
crontab -l | grep codex-datadog-auto-ack
```

Check heartbeat and logs:

```bash
cat ~/.codex/datadog-auto-ack/heartbeat.txt
tail -n 50 ~/.codex/datadog-auto-ack/auto_ack.log
tail -n 50 ~/.codex/datadog-auto-ack/cron.err
```

If cron logs `sqlite3.OperationalError: unable to open database file`, Full Disk Access is still missing for the cron-launched process.

## Debug Safely

Run one poll manually:

```bash
~/.codex/datadog-auto-ack/run.sh
```

Use dry-run mode before trusting a new sender or pattern:

```bash
AUTO_ACK_DRY_RUN=1 AUTO_ACK_TARGET=43152 python3 scripts/imessage_auto_ack.py --once
```

The log intentionally records message IDs and chosen replies, not alert bodies.

## Uninstall

Use:

```bash
scripts/uninstall_cron.sh
```

This removes only crontab lines tagged `codex-datadog-auto-ack`; it leaves runtime logs and state in `~/.codex/datadog-auto-ack` for audit unless the user deletes them.
