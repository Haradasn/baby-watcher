"""
voice.py — Piper TTSでメッセージを音声合成し、スピーカーから再生する

Piperが未インストールの環境(開発機など)でも動くよう、
失敗したら再生をスキップしてテキスト長から推定した長さだけ返す。
"""
import contextlib
import os
import subprocess
import tempfile
import wave

PIPER_MODEL = os.environ.get("PIPER_MODEL", os.path.expanduser("~/piper/ja_JP-voice.onnx"))
VOICE_VOLUME = os.environ.get("VOICE_VOLUME", "0.1")
AUDIO_DEVICE = os.environ.get("AUDIO_DEVICE", "plughw:CARD=MAX98357A,DEV=0")


def _estimate_duration(text: str) -> float:
    return max(1.0, len(text) * 0.28)


def synthesize(text: str) -> str | None:
    """textを音声合成し、一時wavファイルのパスを返す。失敗したらNone"""
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(
            [
                "python3", "-m", "piper",
                "-m", PIPER_MODEL,
                "-f", path,
                "--volume", VOICE_VOLUME,
            ],
            input=text.encode("utf-8"),
            check=True,
            capture_output=True,
            timeout=15,
        )
        return path
    except Exception as e:
        print(f"  [voice] Piper合成に失敗、無音で進行: {e}")
        os.remove(path)
        return None


def duration_of(wav_path: str) -> float:
    with contextlib.closing(wave.open(wav_path, "rb")) as f:
        return f.getnframes() / float(f.getframerate())


def play(wav_path: str):
    subprocess.Popen(["aplay", "-q", "-D", AUDIO_DEVICE, wav_path])


def speak(text: str) -> float:
    """音声合成して再生する。戻り値は再生時間(秒、顔のリップシンクに使う)"""
    path = synthesize(text)
    if path is None:
        return _estimate_duration(text)
    dur = duration_of(path)
    play(path)
    return dur
