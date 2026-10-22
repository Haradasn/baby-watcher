"""
face.py — GC9A01丸型ディスプレイに表情(目・口)を描画する

ハードウェア未接続の環境でも動くよう、ディスプレイ用ライブラリが
無ければ画像生成だけ行い実機への出力はスキップする。
"""

import time

from PIL import Image, ImageDraw

try:
    import board
    import busio
    import digitalio
    from adafruit_rgb_display import gc9a01

    _spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
    _cs = digitalio.DigitalInOut(board.CE0)
    _dc = digitalio.DigitalInOut(board.D25)
    _rst = digitalio.DigitalInOut(board.D27)
    _disp = gc9a01.GC9A01(_spi, cs=_cs, dc=_dc, rst=_rst, width=240, height=240, rotation=0)
    HAS_HW = True
except Exception:
    _disp = None
    HAS_HW = False

WIDTH = HEIGHT = 240
BG = (8, 8, 12)
EYE = (255, 255, 255)

# 表情ごとのパラメータ(目の高さ倍率、口の開き具合の基準値)
EMOTIONS = {
    "neutral": {"eye_h": 1.0},
    "happy": {"eye_h": 0.55},
    "surprised": {"eye_h": 1.6},
    "sleepy": {"eye_h": 0.2},
    "curious": {"eye_h": 1.15},
}

_last_emotion = "neutral"


def _draw(emotion, mouth_open, dim):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)
    p = EMOTIONS.get(emotion, EMOTIONS["neutral"])

    eye_w = 26
    eye_h = max(4, int(34 * p["eye_h"]))
    for cx in (90, 150):
        d.ellipse(
            [cx - eye_w // 2, 110 - eye_h // 2, cx + eye_w // 2, 110 + eye_h // 2],
            fill=EYE,
        )

    mw, mh = (50, 22) if mouth_open else (36, 6)
    d.ellipse(
        [120 - mw // 2, 165 - mh // 2, 120 + mw // 2, 165 + mh // 2],
        outline=EYE,
        width=4,
    )

    if dim:
        img = Image.eval(img, lambda x: x // 6)
    return img


def show(emotion="neutral", mouth_open=False, dim=False):
    global _last_emotion
    _last_emotion = emotion
    img = _draw(emotion, mouth_open, dim)
    if HAS_HW:
        _disp.image(img)
    return img


def off():
    if HAS_HW:
        _disp.fill(0)


def talk(duration, emotion=None):
    """duration秒かけて口をパクパクさせる簡易リップシンク"""
    emotion = emotion or _last_emotion
    t0 = time.time()
    toggle = False
    while time.time() - t0 < duration:
        show(emotion, mouth_open=toggle)
        toggle = not toggle
        time.sleep(0.15)
    show(emotion, mouth_open=False)
