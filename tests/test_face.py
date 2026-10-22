import face


class TestHasHw:
    def test_no_hardware_in_dev_environment(self):
        # 開発機(このテスト実行環境)にはディスプレイ用ライブラリが無い想定
        assert face.HAS_HW is False


class TestDraw:
    def test_returns_correct_size_image(self):
        img = face._draw("neutral", mouth_open=False, dim=False)
        assert img.size == (face.WIDTH, face.HEIGHT)

    def test_all_known_emotions_render_without_error(self):
        for emotion in face.EMOTIONS:
            img = face._draw(emotion, mouth_open=True, dim=False)
            assert img.size == (face.WIDTH, face.HEIGHT)

    def test_unknown_emotion_falls_back_to_neutral(self):
        img_unknown = face._draw("not-a-real-emotion", mouth_open=False, dim=False)
        img_neutral = face._draw("neutral", mouth_open=False, dim=False)
        assert list(img_unknown.get_flattened_data()) == list(img_neutral.get_flattened_data())

    def test_dim_darkens_the_image(self):
        bright = face._draw("neutral", mouth_open=False, dim=False)
        dark = face._draw("neutral", mouth_open=False, dim=True)
        bright_total = sum(sum(px) for px in bright.get_flattened_data())
        dark_total = sum(sum(px) for px in dark.get_flattened_data())
        assert dark_total < bright_total


class TestShowOffTalk:
    def test_show_returns_image_and_updates_last_emotion(self):
        img = face.show("happy")
        assert img.size == (face.WIDTH, face.HEIGHT)
        assert face._last_emotion == "happy"

    def test_off_does_not_raise_without_hardware(self):
        face.off()  # HAS_HW=False なので何もしないだけで例外は出ない

    def test_talk_runs_for_given_duration_without_hardware(self):
        # ハードウェア無しでもループが止まり、例外が出ないことを確認
        face.talk(0.05, "happy")
