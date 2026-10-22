"""
baby_watcher.py — 動きを検知した時だけ画像をLLMに見せて、状況を赤ちゃんに語りかけ、スマホにも通知する

構成:  カメラ(首振り台) → 動き検知(ローカル) → Claude API(画像を読む)
       → 表情(GC9A01) + 音声(Piper TTS) + 首振り(PCA9685/SG90) + ntfyでスマホ通知
画像はデフォルトではメモリ上でだけ扱い、ディスクには保存しません(--save-framesで明示的に有効化した場合のみ保存)。

※ 見守りの補助です。赤ちゃんの安全確認の代わりにはなりません。
※ ぬいぐるみには埋め込まず、ベビーベッドのそばの棚などに据え置いて使う想定です。

使い方:
  1. pip install anthropic opencv-python-headless requests pillow
     (Raspberry Pi 本体では picamera2 / adafruit-circuitpython-servokit /
      adafruit-circuitpython-rgb-display / piper-tts も。開発機ではこれらが無くても動きます)
  2. 環境変数を設定
       export ANTHROPIC_API_KEY=sk-ant-...
       export NTFY_TOPIC=好きな長くてランダムな文字列   (例: baby-7f3k9q2xw8)
  3. スマホに ntfy アプリを入れ、同じトピック名を購読
  4. python baby_watcher.py          (PCのWebカメラでテスト)
     python baby_watcher.py --picam  (Raspberry Pi カメラ)
"""

import argparse
import base64
import json
import os
import time
from datetime import datetime

import anthropic
import cv2
import requests

import face
import neck
import voice

# ===== 調整用パラメータ =====
MODEL = "claude-haiku-5-5"  # 安くて速いモデル。精度が足りなければ claude-sonnet-5-5
MOTION_THRESHOLD = 0.005  # 画面の何割が変化したら「動いた」とみなすか (0.5%)
MIN_LLM_INTERVAL = 30  # LLMに送る最短間隔(秒)。API代の節約
MIN_NOTIFY_INTERVAL = 30  # 通知の最短間隔(秒)。語りかけ用途のため短め
IMAGE_WIDTH = 640  # 送る画像の幅。小さいほど安く、送る情報も減る
ACTIVE_HOURS = None  # 例: (20, 7) で 20時〜翌7時だけ動かす。None なら常時
QUIET_HOURS = (21, 7)  # この時間帯は表情を消灯しTTSも喋らない(通知だけは送る)
SCAN_DWELL = 8  # 自律巡回で1つのプリセット位置に留まる秒数

PAPA_HINT = os.environ.get("PAPA_HINT", "")
MAMA_HINT = os.environ.get("MAMA_HINT", "")


def _build_system_prompt():
    person_section = """人物の呼び方:
- 見た目が男性の大人 → 「パパ」と呼ぶ
- 見た目が女性の大人 → 「ママ」と呼ぶ
- 性別が判別できない場合 → 「大人の人」と呼ぶ"""
    if PAPA_HINT:
        person_section += f"\n- ただし次の特徴の人物は性別によらず「パパ」優先: {PAPA_HINT}"
    if MAMA_HINT:
        person_section += f"\n- ただし次の特徴の人物は性別によらず「ママ」優先: {MAMA_HINT}"

    return f"""あなたは赤ちゃんに語りかけるナレーターです。
寝室カメラの静止画を見て、赤ちゃんに周りの様子をやさしく伝えてください。
口調は「〜しているよ」「〜だね」のように、赤ちゃんに話しかける温かいトーンで。

{person_section}

観察のポイント: 「人がいる」だけで終わらせず、画像の中の具体的な手がかりを最低1つ拾ってください。
- 人の動作(抱っこしている、スマホを見ている、しゃがんでいる、こちらを向いているなど)
- 身につけているもの・持っているもの(服の色、メガネ、哺乳瓶、タオル、おもちゃなど)
- 部屋の変化(カーテン、照明、時計、窓の外の明るさ、床に落ちている物など)
- 赤ちゃん自身の様子(向き、手足の動き、表情)
同じような場面でも、毎回違う手がかりに注目して言い回しを変えてください。決まり文句の使い回しは避けること。

伝える例:
- 青いシャツの大人の人が、抱っこしようとしてるよ
- 大人の人がスマホを見ながらそばにいるね
- カーテンが開いて、お部屋が明るくなったよ
- 赤ちゃんの足がぴょこぴょこ動いてるね
伝えない例: 何も変化がない、カメラのノイズだけ

notifyの判断: 赤ちゃんに何か伝えられることがあればtrue。伝えることが特になければfalse。
emotionは状況に合わせて次から選ぶ: neutral, happy, surprised, sleepy, curious

必ず次のJSONだけを返してください:
{{"notify": true/false, "message": "赤ちゃんへの語りかけ30文字以内", "emotion": "neutral/happy/surprised/sleepy/curious"}}
"""


SYSTEM_PROMPT = _build_system_prompt()


def open_camera(use_picam: bool):
    if use_picam:
        from picamera2 import Picamera2

        cam = Picamera2()
        cam.configure(
            cam.create_preview_configuration(main={"size": (1280, 720), "format": "RGB888"})
        )
        cam.start()
        time.sleep(2)
        return lambda: cam.capture_array()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("カメラが開けません")

    def read():
        ok, frame = cap.read()
        return frame if ok else None

    return read


def to_gray(frame):
    return cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)


def motion_info(prev_gray, gray):
    """動き比率と、動きの重心位置(画面中心を0とした-1.0〜1.0)を返す"""
    diff = cv2.absdiff(prev_gray, gray)
    _, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    ratio = cv2.countNonZero(mask) / mask.size

    ys, xs = mask.nonzero()
    if len(xs) == 0:
        return ratio, 0.0, 0.0
    h, w = mask.shape
    cx, cy = xs.mean(), ys.mean()
    dx = (cx - w / 2) / (w / 2)
    dy = (cy - h / 2) / (h / 2)
    return ratio, dx, dy


def to_jpeg_bytes(frame):
    h, w = frame.shape[:2]
    if w > IMAGE_WIDTH:
        frame = cv2.resize(frame, (IMAGE_WIDTH, int(h * IMAGE_WIDTH / w)))
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return buf.tobytes()


def save_debug_frame(save_dir, jpeg_bytes):
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, f"{datetime.now():%Y%m%d_%H%M%S_%f}.jpg")
    with open(path, "wb") as f:
        f.write(jpeg_bytes)


def ask_llm(client, frame, save_dir=None):
    jpeg_bytes = to_jpeg_bytes(frame)
    if save_dir:
        save_debug_frame(save_dir, jpeg_bytes)
    res = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64.b64encode(jpeg_bytes).decode(),
                        },
                    },
                    {
                        "type": "text",
                        "text": f"現在時刻 {datetime.now():%H:%M}。判断してください。",
                    },
                ],
            }
        ],
    )
    text = next(b.text for b in res.content if b.type == "text").strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def notify(topic, message):
    requests.post(f"https://ntfy.sh/{topic}", data=message.encode("utf-8"), timeout=10)


def _in_hours(hours):
    if hours is None:
        return False
    start, end = hours
    h = datetime.now().hour
    return (start <= h or h < end) if start > end else (start <= h < end)


def in_active_hours():
    return ACTIVE_HOURS is None or _in_hours(ACTIVE_HOURS)


def in_quiet_hours():
    return _in_hours(QUIET_HOURS)


def react_and_speak(client, frame, dx, dy, topic, now, last_notify, dry_run, save_dir=None):
    """動きを検知した時の一連の反応: 首を向ける→判定→表情/発話/通知"""
    neck.react_toward(dx, dy)

    try:
        result = ask_llm(client, frame, save_dir=save_dir)
    except Exception as e:
        print(f"[{datetime.now():%H:%M:%S}] LLMエラー: {e}")
        neck.center()
        return last_notify

    emotion = result.get("emotion", "neutral")
    message = result.get("message", "")
    print(f"[{datetime.now():%H:%M:%S}] 反応 → {result}")

    quiet = in_quiet_hours()
    face.show(emotion, dim=quiet)

    if result.get("notify"):
        if now - last_notify >= MIN_NOTIFY_INTERVAL:
            last_notify = now
            if not dry_run:
                notify(topic, message or "動きがありました")
            print("  → 通知送信")

            if not quiet:
                dur = voice.speak(message) if message else 0
                if dur:
                    face.talk(dur, emotion)
            else:
                print("  → 夜間のため発話は抑制(通知のみ)")
        else:
            wait = MIN_NOTIFY_INTERVAL - (now - last_notify)
            print(f"  → 間引き(あと{wait:.0f}秒は通知しません)")

    time.sleep(1.0)
    neck.center()
    if quiet:
        face.off()
    return last_notify


def idle_scan_step(read, baselines, scan_idx, last_move):
    """自律巡回: 留まり時間が過ぎたら次のプリセット位置へ首を振り、基準フレームを取り直す"""
    pos = neck.SCAN_POSITIONS[scan_idx]
    neck.move_to(*pos)
    frame = read()
    if frame is not None:
        baselines[pos] = to_gray(frame)
    return (scan_idx + 1) % len(neck.SCAN_POSITIONS), time.time()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--picam", action="store_true", help="Raspberry Pi カメラを使う")
    parser.add_argument("--dry-run", action="store_true", help="通知せず結果を表示だけする")
    parser.add_argument(
        "--no-neck", action="store_true", help="首振り巡回をせず正面固定で動かす(検証用)"
    )
    parser.add_argument(
        "--save-frames",
        metavar="DIR",
        default=None,
        help="LLMに送った画像を指定ディレクトリに保存する(確認用。デフォルトは保存しない)",
    )
    args = parser.parse_args()

    topic = os.environ.get("NTFY_TOPIC")
    if not topic and not args.dry_run:
        raise SystemExit("NTFY_TOPIC を設定してください(テストだけなら --dry-run)")

    client = anthropic.Anthropic()
    read = open_camera(args.picam)
    last_llm = last_notify = 0.0
    print("見守りを開始しました。Ctrl+C で終了")
    if neck.HAS_HW:
        print("  首振りハードウェア: 有効")
    else:
        print("  首振りハードウェア: 未検出(ソフトウェアのみでシミュレート)")

    baselines = {}
    scan_idx = 0
    if args.no_neck:
        neck.center()
    else:
        neck.move_to(*neck.SCAN_POSITIONS[0])
    last_move = time.time()
    # 各プリセット位置の基準フレームは、巡回しながら最初の1周で順次取得する

    while True:
        pos = neck.current_position()

        # 巡回モード: 留まり時間が過ぎたら次の位置へ(--no-neckなら巡回しない)
        if not args.no_neck and time.time() - last_move >= SCAN_DWELL:
            scan_idx, last_move = idle_scan_step(read, baselines, scan_idx, last_move)
            continue  # 移動直後のフレームは基準フレームとして使ったので今回は検知をスキップ

        frame = read()
        if frame is None:
            time.sleep(1)
            continue

        gray = to_gray(frame)
        prev_gray = baselines.get(pos)
        if prev_gray is None:
            baselines[pos] = gray
            time.sleep(0.5)
            continue

        ratio, dx, dy = motion_info(prev_gray, gray)
        baselines[pos] = gray  # 基準フレームは常に最新に更新(照明変化などに追従)

        now = time.time()
        if ratio >= MOTION_THRESHOLD and in_active_hours() and now - last_llm >= MIN_LLM_INTERVAL:
            last_llm = now
            last_notify = react_and_speak(
                client,
                frame,
                dx,
                dy,
                topic,
                now,
                last_notify,
                args.dry_run,
                save_dir=args.save_frames,
            )
            last_move = time.time()  # 反応後は巡回タイマーをリセット

        time.sleep(0.5)


if __name__ == "__main__":
    main()
