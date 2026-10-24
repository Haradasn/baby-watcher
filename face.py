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
    from adafruit_rgb_display import gc9a01a

    _spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
    _cs = digitalio.DigitalInOut(board.CE0)
    _dc = digitalio.DigitalInOut(board.D25)
    _rst = digitalio.DigitalInOut(board.D27)
    _disp = gc9a01a.GC9A01A(_spi, cs=_cs, dc=_dc, rst=_rst, width=240, height=240, rotation=0)
    HAS_HW = True
except Exception:
    _disp = None
    HAS_HW = False

WIDTH = HEIGHT = 240
SCLERA = (255, 255, 255)
IRIS = (101, 67, 40)  # 温かみのあるブラウン
PUPIL = (35, 24, 18)
SHINE = (255, 255, 255)
CHEEK = (255, 150, 165)
INK = (120, 80, 65)  # 線画(目・口のアウトライン)の色

# 表情ごとのパラメータ:
#   bg    背景色(表情でやさしく変える)
#   eye   目の形("open"=虹彩付きの丸目, "closed_up"=^の笑い目, "closed_flat"=眠そうな目)
#   scale 目の大きさ倍率
#   mouth 口の形
EMOTIONS = {
    "neutral": {"bg": (255, 243, 230), "eye": "open", "scale": 1.0, "mouth": "smile_s"},
    "happy": {"bg": (255, 228, 196), "eye": "closed_up", "scale": 1.0, "mouth": "smile_l"},
    "surprised": {"bg": (255, 250, 210), "eye": "open", "scale": 1.35, "mouth": "o"},
    "sleepy": {"bg": (224, 224, 245), "eye": "closed_flat", "scale": 1.0, "mouth": "flat"},
    "curious": {"bg": (218, 240, 255), "eye": "open", "scale": 1.1, "mouth": "smile_s"},
}

_last_emotion = "neutral"


def _draw_eye(d, cx, cy, style, scale):
    w = h = int(34 * scale)
    if style == "open":
        d.ellipse([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2], fill=SCLERA)
        iw = ih = int(w * 0.62)
        d.ellipse([cx - iw // 2, cy - ih // 2, cx + iw // 2, cy + ih // 2], fill=IRIS)
        pw = int(w * 0.3)
        d.ellipse([cx - pw // 2, cy - pw // 2, cx + pw // 2, cy + pw // 2], fill=PUPIL)
        sw = max(3, int(w * 0.16))
        sx, sy = cx - iw // 4, cy - ih // 4
        d.ellipse([sx - sw // 2, sy - sw // 2, sx + sw // 2, sy + sw // 2], fill=SHINE)
    elif style == "closed_up":
        # ^ の形の笑い目(円の上側だけ弧を描く)
        d.arc([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2], start=200, end=340, fill=INK, width=5)
    else:  # closed_flat (眠そう)
        d.line([cx - w // 2 + 3, cy - 2, cx + w // 2 - 3, cy + 5], fill=INK, width=5)


def _draw_mouth(d, style, mouth_open):
    cx, cy = 120, 168
    if mouth_open:
        d.ellipse([cx - 25, cy - 12, cx + 25, cy + 12], fill=INK)
        return
    if style == "o":
        d.ellipse([cx - 16, cy - 10, cx + 16, cy + 10], outline=INK, width=4)
    elif style == "flat":
        d.line([cx - 14, cy, cx + 14, cy], fill=INK, width=4)
    elif style == "smile_l":
        d.arc([cx - 30, cy - 22, cx + 30, cy + 18], start=15, end=165, fill=INK, width=6)
    else:  # smile_s
        d.arc([cx - 20, cy - 12, cx + 20, cy + 14], start=20, end=160, fill=INK, width=5)


def _draw(emotion, mouth_open, dim):
    p = EMOTIONS.get(emotion, EMOTIONS["neutral"])
    img = Image.new("RGB", (WIDTH, HEIGHT), p["bg"])
    d = ImageDraw.Draw(img)

    for cx in (88, 152):
        _draw_eye(d, cx, 108, p["eye"], p["scale"])

    for cx in (58, 182):  # ほっぺ
        d.ellipse([cx - 15, 142 - 10, cx + 15, 142 + 10], fill=CHEEK)

    _draw_mouth(d, p["mouth"], mouth_open)

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
