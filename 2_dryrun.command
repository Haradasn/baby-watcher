#!/bin/bash
# ダブルクリックで動作テスト（通知は送らず、判断結果を表示するだけ）。Ctrl+C で終了
cd "$(dirname "$0")"
./run.sh --dry-run
read -n 1 -s -r -p "終了しました。何かキーを押すと閉じます。"
