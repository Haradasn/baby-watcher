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
# チルトは物理的な組み直し(ホーンの付け直し・カメラの反転)で角度と向きの対応が
# 反転したため、「うつむき」はtilt=90より大きい側になった(以前は75だった)。
SCAN_POSITIONS = [
    (90, 90),  # 正面
    (60, 85),  # 左(少し上向き)
    (120, 85),  # 右(少し上向き)
    (90, 105),  # うつむき
]

SETTLE_SEC = 0.4  # 動かした後、静止するまで待つ時間(この間は動き検知を止める)

# react_toward の振り幅。チルトは可動域(60度)がパン(120度)の半分なので、
# 同じ「見た目の動き量」になるよう、パンより少し小さい値にしてあるが、
# 以前(パン25/チルト15)は控えめすぎて「動きを追ってる感」が薄かったので強めた。
REACT_PAN_STRENGTH = 45
REACT_TILT_STRENGTH = 45

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


def react_toward(dx, dy, pan_strength=REACT_PAN_STRENGTH, tilt_strength=REACT_TILT_STRENGTH):
    """
    動きの重心オフセット(dx, dy: 画面中心を0とした-1.0〜1.0の相対位置)の
    方向へ首を振る。dxが+なら画面右→首は左(パン角を下げる)方向に向く。
    dyが+(画面下で検知)なら、首は下(チルト角を上げる)方向に向く
    (実機で確認: ホーンの付け直し・カメラの反転でチルトは角度と向きの対応が
    パンと逆になっている。tilt=120側が物理的には下向き)。

    「今向いている角度」からの相対移動にする(固定の正面を基準にしない)。固定の
    正面を基準にすると、追いついて画面中央に来る(dxが0に近づく)たびに計算結果が
    また正面(90度)に戻ろうとしてしまい、追従にならず往復するだけになるため。
    """
    pan = _cur_pan - dx * pan_strength
    tilt = _cur_tilt + dy * tilt_strength
    return move_to(pan, tilt)


def center():
    return move_to(PAN_CENTER, TILT_CENTER)
