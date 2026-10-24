import neck


class TestHasHw:
    def test_no_hardware_in_dev_environment(self):
        assert neck.HAS_HW is False


class TestClamp:
    def test_value_within_range_is_unchanged(self):
        assert neck._clamp(50, 0, 100) == 50

    def test_value_below_range_is_clamped_to_min(self):
        assert neck._clamp(-10, 0, 100) == 0

    def test_value_above_range_is_clamped_to_max(self):
        assert neck._clamp(150, 0, 100) == 100


class TestMoveTo:
    def test_updates_current_position_within_range(self):
        pan, tilt = neck.move_to(90, 90)
        assert (pan, tilt) == (90, 90)
        assert neck.current_position() == (90, 90)

    def test_clamps_pan_to_pan_range(self):
        lo, hi = neck.PAN_RANGE
        pan, _ = neck.move_to(hi + 100, 90)
        assert pan == hi
        pan, _ = neck.move_to(lo - 100, 90)
        assert pan == lo

    def test_clamps_tilt_to_tilt_range(self):
        lo, hi = neck.TILT_RANGE
        _, tilt = neck.move_to(90, hi + 100)
        assert tilt == hi
        _, tilt = neck.move_to(90, lo - 100)
        assert tilt == lo


class TestReactToward:
    def setup_method(self):
        # react_toward は「今向いている角度」からの相対移動なので、他のテストが
        # 残した状態に影響されないよう、各テストの前に正面へリセットする。
        neck.center()

    def test_positive_dx_turns_pan_below_center(self):
        # dxが+(画面右で動き検知)なら、首は左側(パン角を下げる)方向に向く
        pan, _ = neck.react_toward(dx=1.0, dy=0.0)
        assert pan < neck.PAN_CENTER

    def test_negative_dx_turns_pan_above_center(self):
        pan, _ = neck.react_toward(dx=-1.0, dy=0.0)
        assert pan > neck.PAN_CENTER

    def test_zero_offset_stays_near_center(self):
        pan, tilt = neck.react_toward(dx=0.0, dy=0.0)
        assert pan == neck.PAN_CENTER
        assert tilt == neck.TILT_CENTER

    def test_repeated_calls_keep_following_same_direction(self):
        # 固定の正面を基準にすると、一度追いついて(dxが0に近づくと)また正面に
        # 戻ろうとしてしまう。現在角度基準なら、同方向の動きが続く限りさらに
        # 同方向へ進み続ける(戻ろうとしない)はず。
        pan1, _ = neck.react_toward(dx=0.5, dy=0.0)
        pan2, _ = neck.react_toward(dx=0.5, dy=0.0)
        assert pan2 < pan1


class TestCenter:
    def test_returns_to_center_position(self):
        neck.move_to(60, 70)
        pan, tilt = neck.center()
        assert (pan, tilt) == (neck.PAN_CENTER, neck.TILT_CENTER)
        assert neck.current_position() == (neck.PAN_CENTER, neck.TILT_CENTER)
