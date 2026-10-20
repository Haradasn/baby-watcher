# 引き継ぎメモ: 赤ちゃん見守りエージェント (baby-watcher)

## 目的
フィジカルAIに参入したい個人が、手元でPoCする第一歩として作っている。
赤ちゃん関連の「LLM/エージェントが主役で、物理的なセンサー入力のあるもの」を目指す。
(ぴよログとは被らないこと。ぴよログは公式APIなし、Alexa等の音声入力のみ)

## 現在の構成
カメラ → 動き検知(ローカル) → Claude API(画像を読む) → ntfyでスマホ通知
- baby_watcher.py : 本体。動きがあった時だけ画像をAPIに送る。画像は保存しない
- setup.sh / run.sh : 仮想環境の作成、設定を読み込んで実行
- 1_setup.command / 2_dryrun.command / 3_run.command : ダブルクリック用
- config.sh : setup.sh が自動生成。APIキーと、ランダムなNTFY_TOPICを書く(他人に見せない)

## 済んでいること
- プログラムの作成。カメラとAPIを使わない部分(動き検知、画像縮小、JSON取り出し、時間帯判定)は
  疑似データでテスト済み
- ファイルをMacの ~/repo/baby-watcher に配置済み

## まだ実行していないこと(ここから再開)
1. ./setup.sh を実行 (venv作成 + pip install anthropic opencv-python-headless requests)
2. config.sh の ANTHROPIC_API_KEY を本人が設定  ← Claudeは入力しない。本人が行う
3. ./run.sh --dry-run でカメラ+API実動作を確認 (初回はカメラ許可が必要 ← 本人が許可)
4. ntfyアプリでNTFY_TOPICを購読し、./run.sh で通知まで確認

## 方針・好み
- LLMやAIエージェントを使って「すごっ」と感じられるものにしたい
- 赤ちゃんの手が届く物は作らない。見守りは補助で、安全確認の代わりにしない
- コスト重視: 機械的な作業は小さいモデル(Haiku/Sonnet)でよい
- プログラムの既定モデルは claude-haiku-5-5。精度が足りなければ claude-sonnet-5-5

## 次の候補(動作確認の後)
- マイクで泣き声も検知し、画像と合わせて判断する
- ライトやホワイトノイズの自動制御(フィジカル要素)
- Raspberry Pi 5 + カメラモジュールへ移行 (--picam オプションは実装済み、実機は未検証)
- プライバシー重視で、Ollama等のローカルLLMに差し替える案(Mシリーズ Mac で試せる)

## 注意
- 前のセッションのシェルはMac本体ではなく隔離Linux環境だった。
  Mac本体で実行するには、ローカルのセッションが必要
- 見落としや誤通知は前提。感度は baby_watcher.py 冒頭のパラメータで調整する
