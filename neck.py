"""
neck.py — PCA9685経由でSG90サーボ2個(パン/チルト)を制御する

ハードウェア未接続の環境(開発機など)でも import エラーにならないよう、
adafruit-circuitpython-servokit が無ければソフトウェア的に no-op で動く。
"""

import time

try:
    from adafruit_servokit import ServoKit

    _kit = ServoKit(channels=16)
    HAS_HW = True
except Exception:
    _kit = None
    HAS_HW = False

PAN_CH, TILT_CH = 0, 1
PAN_CENTER, TILT_CENTER = 90, 90

# 安全マージンを持たせた可動範囲(機構に無理な力をかけない)
PAN_RANGE = (30, 150)
TILT_RANGE = (60, 120)

# 自律巡回で順番に見るプリセット位置 (pan, tilt)
SCAN_POSITIONS = [
    (90, 90),  # 正面
    (60, 95),  # 左
    (120, 95),  # 右
    (90, 75),  # うつむき
]

SETTLE_SEC = 0.4  # 動かした後、静止するまで待つ時間(この間は動き検知を止める)

_cur_pan, _cur_tilt = PAN_CENTER, TILT_CENTER


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def move_to(pan, tilt):
    """指定角度へ首を動かし、安定するまで待つ。戻り値: 実際にセットした角度"""
    global _cur_pan, _cur_tilt
    pan = _clamp(pan, *PAN_RANGE)
    tilt = _clamp(tilt, *TILT_RANGE)
    if HAS_HW:
        _kit.servo[PAN_CH].angle = pan
        _kit.servo[TILT_CH].angle = tilt
    _cur_pan, _cur_tilt = pan, tilt
    time.sleep(SETTLE_SEC)
    return pan, tilt


def current_position():
    return _cur_pan, _cur_tilt


def react_toward(dx, dy, strength=25):
    """
    動きの重心オフセット(dx, dy: 画面中心を0とした-1.0〜1.0の相対位置)の
    方向へ首を振る。dxが+なら画面右→首は左(パン角を下げる)方向に向く。
    """
    pan = PAN_CENTER - dx * strength
    tilt = TILT_CENTER - dy * (strength * 0.6)
    return move_to(pan, tilt)


def center():
    return move_to(PAN_CENTER, TILT_CENTER)
