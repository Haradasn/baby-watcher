#!/bin/bash
# ダブルクリックでセットアップ → 終わったら config.sh をエディタで開く
cd "$(dirname "$0")"
./setup.sh && open -e config.sh
echo ""
read -n 1 -s -r -p "config.sh にAPIキーを書いて保存したら、2_dryrun.command を開いてください。何かキーを押すと閉じます。"
