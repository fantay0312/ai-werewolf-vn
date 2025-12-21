import pytest
from app.core.judge import JudgeSystem
from app.models.game_state import GamePhase, Camp

class TestJudgeSystem:
    @pytest.fixture
    def judge(self):
        return JudgeSystem()

    def test_generate_broadcast(self, judge):
        assert judge.generate_broadcast("night_start") == "天黑请闭眼"
        assert judge.generate_broadcast("day_start") == "天亮了，请睁眼"
        assert judge.generate_broadcast("death_announce", dead_ids=[1, 2]) == "昨晚1, 2号玩家死亡"
        assert judge.generate_broadcast("death_announce", dead_ids=[]) == "昨晚是平安夜"
        assert judge.generate_broadcast("game_over", winner=Camp.GOOD) == "游戏结束，好人阵营胜利"

    def test_get_phase_title(self, judge):
        assert judge.get_phase_title(GamePhase.NIGHT_START) == "夜晚降临"
        assert judge.get_phase_title(GamePhase.DAY_DISCUSS) == "自由讨论"

    def test_determine_speaking_order(self, judge):
        alive_ids = [1, 2, 3, 4, 5]
        
        # Test random order (basic check)
        order = judge.determine_speaking_order(alive_ids, sheriff_id=None)
        assert len(order) == 5
        assert set(order) == set(alive_ids)
        
        # Test sheriff last
        sheriff_id = 3
        order_with_sheriff = judge.determine_speaking_order(alive_ids, sheriff_id=sheriff_id)
        assert order_with_sheriff[-1] == sheriff_id
        
    def test_get_time_limit(self, judge):
        assert judge.get_time_limit(GamePhase.DAY_DISCUSS) == 60
        assert judge.get_time_limit(GamePhase.DAY_VOTE) == 30
