#!/bin/bash
# 使い方: ./run.sh --dry-run   (通知せず結果を表示)
#         ./run.sh             (スマホに通知)
cd "$(dirname "$0")"
source .venv/bin/activate
source config.sh
exec python -u baby_watcher.py "$@"
