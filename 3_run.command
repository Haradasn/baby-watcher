#!/bin/bash
# ダブルクリックで見守り開始（スマホに通知）。Ctrl+C で終了
cd "$(dirname "$0")"
./run.sh
read -n 1 -s -r -p "終了しました。何かキーを押すと閉じます。"
