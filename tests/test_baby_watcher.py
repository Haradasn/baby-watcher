import numpy as np
import pytest

import baby_watcher


@pytest.fixture(autouse=True)
def _reset_hints():
    """PAPA_HINT/MAMA_HINTはモジュールグローバルなので、各テスト後に元に戻す"""
    orig_papa, orig_mama = baby_watcher.PAPA_HINT, baby_watcher.MAMA_HINT
    yield
    baby_watcher.PAPA_HINT, baby_watcher.MAMA_HINT = orig_papa, orig_mama


def make_frame(h=64, w=64, value=0):
    return np.full((h, w, 3), value, dtype=np.uint8)


class TestBuildSystemPrompt:
    def test_default_uses_gender_based_naming(self):
        baby_watcher.PAPA_HINT = ""
        baby_watcher.MAMA_HINT = ""
        prompt = baby_watcher._build_system_prompt()
        assert "見た目が男性の大人" in prompt
        assert "見た目が女性の大人" in prompt
        assert "パパ」優先" not in prompt

    def test_papa_hint_adds_override_rule(self):
        baby_watcher.PAPA_HINT = "メガネをかけている男性"
        baby_watcher.MAMA_HINT = ""
        prompt = baby_watcher._build_system_prompt()
        assert "メガネをかけている男性" in prompt
        assert "パパ」優先" in prompt
        assert "ママ」優先" not in prompt

    def test_both_hints_add_both_override_rules(self):
        baby_watcher.PAPA_HINT = "メガネの男性"
        baby_watcher.MAMA_HINT = "髪が長い女性"
        prompt = baby_watcher._build_system_prompt()
        assert "パパ」優先" in prompt
        assert "ママ」優先" in prompt

    def test_always_returns_valid_json_schema_instruction(self):
        prompt = baby_watcher._build_system_prompt()
        assert '"notify"' in prompt
        assert '"message"' in prompt
        assert '"emotion"' in prompt


class TestMotionInfo:
    def test_no_motion_returns_zero_ratio_and_center(self):
        gray = baby_watcher.to_gray(make_frame(value=100))
        ratio, dx, dy = baby_watcher.motion_info(gray, gray)
        assert ratio == 0.0
        assert dx == 0.0
        assert dy == 0.0

    def test_motion_on_right_side_gives_positive_dx(self):
        prev = make_frame(value=0)
        cur = make_frame(value=0)
        cur[:, 48:, :] = 255  # 右側だけ変化させる
        prev_gray = baby_watcher.to_gray(prev)
        gray = baby_watcher.to_gray(cur)
        ratio, dx, dy = baby_watcher.motion_info(prev_gray, gray)
        assert ratio > 0
        assert dx > 0

    def test_motion_on_bottom_gives_positive_dy(self):
        prev = make_frame(value=0)
        cur = make_frame(value=0)
        cur[48:, :, :] = 255  # 下側だけ変化させる
        prev_gray = baby_watcher.to_gray(prev)
        gray = baby_watcher.to_gray(cur)
        ratio, dx, dy = baby_watcher.motion_info(prev_gray, gray)
        assert dy > 0


class TestToJpegBytes:
    def test_returns_nonempty_jpeg_bytes(self):
        frame = make_frame(h=100, w=100, value=128)
        data = baby_watcher.to_jpeg_bytes(frame)
        assert isinstance(data, bytes)
        assert data[:2] == b"\xff\xd8"  # JPEG magic bytes

    def test_wide_frame_is_resized_to_image_width(self):
        frame = make_frame(h=200, w=baby_watcher.IMAGE_WIDTH * 2, value=50)
        data = baby_watcher.to_jpeg_bytes(frame)
        assert isinstance(data, bytes) and len(data) > 0

    def test_narrow_frame_is_not_upscaled(self):
        small_w = baby_watcher.IMAGE_WIDTH // 2
        frame = make_frame(h=50, w=small_w, value=50)
        data = baby_watcher.to_jpeg_bytes(frame)
        assert isinstance(data, bytes) and len(data) > 0


class TestSaveDebugFrame:
    def test_writes_jpeg_file_into_directory(self, tmp_path):
        jpeg_bytes = b"\xff\xd8fakejpegdata"
        baby_watcher.save_debug_frame(str(tmp_path), jpeg_bytes)
        files = list(tmp_path.glob("*.jpg"))
        assert len(files) == 1
        assert files[0].read_bytes() == jpeg_bytes

    def test_creates_directory_if_missing(self, tmp_path):
        target = tmp_path / "nested" / "debug_frames"
        baby_watcher.save_debug_frame(str(target), b"\xff\xd8x")
        assert target.is_dir()
        assert len(list(target.glob("*.jpg"))) == 1


class TestActiveAndQuietHours:
    def test_in_hours_none_is_always_false(self):
        assert baby_watcher._in_hours(None) is False

    def test_in_hours_same_day_range(self, monkeypatch):
        class FakeDatetime(baby_watcher.datetime):
            @classmethod
            def now(cls):
                return cls(2026, 1, 1, 10, 0)

        monkeypatch.setattr(baby_watcher, "datetime", FakeDatetime)
        assert baby_watcher._in_hours((9, 17)) is True
        assert baby_watcher._in_hours((11, 17)) is False

    def test_in_hours_overnight_range(self, monkeypatch):
        class FakeDatetimeNight(baby_watcher.datetime):
            @classmethod
            def now(cls):
                return cls(2026, 1, 1, 23, 0)

        monkeypatch.setattr(baby_watcher, "datetime", FakeDatetimeNight)
        assert baby_watcher._in_hours((21, 7)) is True  # 21時〜翌7時の範囲内

        class FakeDatetimeNoon(baby_watcher.datetime):
            @classmethod
            def now(cls):
                return cls(2026, 1, 1, 12, 0)

        monkeypatch.setattr(baby_watcher, "datetime", FakeDatetimeNoon)
        assert baby_watcher._in_hours((21, 7)) is False

    def test_active_hours_none_means_always_active(self, monkeypatch):
        monkeypatch.setattr(baby_watcher, "ACTIVE_HOURS", None)
        assert baby_watcher.in_active_hours() is True


class TestNotify:
    def test_posts_message_to_ntfy_topic(self, monkeypatch):
        calls = {}

        def fake_post(url, data, timeout):
            calls["url"] = url
            calls["data"] = data
            calls["timeout"] = timeout

        monkeypatch.setattr(baby_watcher.requests, "post", fake_post)
        baby_watcher.notify("my-topic", "こんにちは")
        assert calls["url"] == "https://ntfy.sh/my-topic"
        assert calls["data"] == "こんにちは".encode("utf-8")
