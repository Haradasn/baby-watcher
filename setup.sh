#!/bin/bash
# baby-watcher のセットアップ（Macのターミナルで1回だけ実行）
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -q anthropic opencv-python-headless requests pillow
pip install -q ruff pytest  # 開発用(整形・テスト。Pi本体では不要)
# Raspberry Pi本体では以下も必要(開発機ではハードウェアが無くても動きます):
#   pip install adafruit-circuitpython-servokit adafruit-circuitpython-rgb-display
#   pip install 'piper-tts[ja]'  # 日本語音声合成(OpenJTalk同梱)
#   日本語音声モデルを ~/piper/ja_JP-voice.onnx (+.onnx.json) に配置
#   例: https://huggingface.co/rhasspy/piper-voices/tree/main/ja/ja_JP/hi_fi_captain/medium
if [ ! -f config.sh ]; then
  TOPIC="baby-$(openssl rand -hex 6)"
  cat > config.sh <<CFG
# ここにAPIキーを書いてください（このファイルは他人に見せない）
export ANTHROPIC_API_KEY="sk-ant-ここに貼る"
# スマホのntfyアプリでこのトピック名を購読してください
export NTFY_TOPIC="$TOPIC"
# パパ・ママの見た目の特徴（未設定なら「大人の人」と表現します）
# export PAPA_HINT="メガネをかけている男性"
# export MAMA_HINT="髪が長い女性"
CFG
  chmod 600 config.sh
fi
echo ""
echo "セットアップ完了。config.sh にAPIキーを書いてから ./run.sh --dry-run を実行してください。"
