import wave

import pytest

import voice


class TestEstimateDuration:
    def test_short_text_has_minimum_one_second(self):
        assert voice._estimate_duration("") == 1.0
        assert voice._estimate_duration("あ") == 1.0

    def test_longer_text_scales_with_length(self):
        text = "あ" * 20
        assert voice._estimate_duration(text) == pytest.approx(20 * 0.28)


class TestSynthesize:
    def test_returns_none_and_cleans_up_on_piper_failure(self, monkeypatch):
        def fake_run(*args, **kwargs):
            raise FileNotFoundError("piper not found")

        monkeypatch.setattr(voice.subprocess, "run", fake_run)
        removed = {}
        orig_remove = voice.os.remove
        monkeypatch.setattr(
            voice.os, "remove", lambda p: (removed.setdefault("path", p), orig_remove(p))
        )

        path = voice.synthesize("テスト")
        assert path is None
        assert "path" in removed

    def test_returns_path_on_success(self, monkeypatch, tmp_path):
        def fake_run(cmd, input, check, capture_output, timeout):
            # synthesize()が作った一時ファイルパスがコマンド引数に含まれる
            out_path = cmd[cmd.index("-f") + 1]
            with open(out_path, "wb"):
                pass
            return None

        monkeypatch.setattr(voice.subprocess, "run", fake_run)
        path = voice.synthesize("テスト")
        assert path is not None
        assert path.endswith(".wav")


class TestDurationOf:
    def test_reads_wav_duration_in_seconds(self, tmp_path):
        wav_path = tmp_path / "test.wav"
        framerate = 16000
        nframes = framerate * 2  # 2秒分
        with wave.open(str(wav_path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(framerate)
            f.writeframes(b"\x00\x00" * nframes)

        assert voice.duration_of(str(wav_path)) == pytest.approx(2.0)


class TestPlay:
    def test_invokes_aplay_with_configured_device(self, monkeypatch):
        calls = {}

        class FakePopen:
            def __init__(self, cmd):
                calls["cmd"] = cmd

        monkeypatch.setattr(voice.subprocess, "Popen", FakePopen)
        voice.play("/tmp/x.wav")
        assert calls["cmd"] == ["aplay", "-q", "-D", voice.AUDIO_DEVICE, "/tmp/x.wav"]


class TestSpeak:
    def test_falls_back_to_estimated_duration_when_synthesis_fails(self, monkeypatch):
        monkeypatch.setattr(voice, "synthesize", lambda text: None)
        played = []
        monkeypatch.setattr(voice, "play", lambda path: played.append(path))

        dur = voice.speak("こんにちは")
        assert dur == voice._estimate_duration("こんにちは")
        assert played == []

    def test_plays_and_returns_actual_duration_on_success(self, monkeypatch):
        monkeypatch.setattr(voice, "synthesize", lambda text: "/tmp/fake.wav")
        monkeypatch.setattr(voice, "duration_of", lambda path: 3.5)
        played = []
        monkeypatch.setattr(voice, "play", lambda path: played.append(path))

        dur = voice.speak("こんにちは")
        assert dur == 3.5
        assert played == ["/tmp/fake.wav"]
