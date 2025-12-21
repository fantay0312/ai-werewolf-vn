from typing import List, Dict, Optional
import random
import logging
from app.models.game_state import GameState, GamePhase, Camp
from app.core.rules import Rules

logger = logging.getLogger(__name__)

class JudgeSystem:
    """
    法官系统负责：
    1. 生成阶段播报文案
    2. 主持游戏流程
    3. 处理争议裁决
    4. 记录游戏日志
    """
    
    def __init__(self):
        pass
    
    # === 播报生成 ===
    
    def generate_broadcast(self, event_type: str, **kwargs) -> str:
        """
        生成法官播报
        
        event_type可选值：
        - night_start: "天黑请闭眼"
        - day_start: "天亮了，请睁眼"
        - death_announce: "昨晚{}号玩家死亡" / "昨晚是平安夜"
        - last_words: "请{}号玩家发表遗言"
        - sheriff_election: "现在开始警长竞选，请想要竞选的玩家举手"
        - sheriff_elected: "{}号玩家当选警长"
        - no_sheriff: "本局无警长"
        - speech_turn: "请{}号玩家发言"
        - time_up: "发言时间到"
        - vote_start: "请开始投票"
        - vote_result: "投票结果：{}号玩家被放逐" / "平票，无人被放逐"
        - skill_trigger: "{}号玩家发动技能"
        - game_over: "游戏结束，{}阵营胜利"
        """
        if event_type == "night_start":
            return "天黑请闭眼"
        elif event_type == "day_start":
            return "天亮了，请睁眼"
        elif event_type == "death_announce":
            dead_ids = kwargs.get("dead_ids", [])
            if not dead_ids:
                return "昨晚是平安夜"
            else:
                dead_str = ", ".join(map(str, dead_ids))
                return f"昨晚{dead_str}号玩家死亡"
        elif event_type == "last_words":
            player_id = kwargs.get("player_id")
            return f"请{player_id}号玩家发表遗言"
        elif event_type == "sheriff_election":
            return "现在开始警长竞选，请想要竞选的玩家举手"
        elif event_type == "sheriff_elected":
            sheriff_id = kwargs.get("sheriff_id")
            return f"{sheriff_id}号玩家当选警长"
        elif event_type == "no_sheriff":
            return "本局无警长"
        elif event_type == "speech_turn":
            player_id = kwargs.get("player_id")
            return f"请{player_id}号玩家发言"
        elif event_type == "time_up":
            return "发言时间到"
        elif event_type == "vote_start":
            return "请开始投票"
        elif event_type == "vote_result":
            target_id = kwargs.get("target_id")
            if target_id:
                return f"投票结果：{target_id}号玩家被放逐"
            else:
                return "平票，无人被放逐"
        elif event_type == "skill_trigger":
            player_id = kwargs.get("player_id")
            return f"{player_id}号玩家发动技能"
        elif event_type == "game_over":
            winner = kwargs.get("winner")
            winner_str = "好人" if winner == Camp.GOOD else "狼人"
            return f"游戏结束，{winner_str}阵营胜利"
        
        return ""
    
    # === 阶段文案 ===
    
    def get_phase_title(self, phase: GamePhase) -> str:
        """获取阶段标题"""
        phase_titles = {
            GamePhase.NIGHT_START: "夜晚降临",
            GamePhase.NIGHT_WOLF_DISCUSS: "狼人请睁眼",
            GamePhase.NIGHT_SEER: "预言家请睁眼",
            GamePhase.NIGHT_WITCH: "女巫请睁眼",
            GamePhase.NIGHT_GUARD: "守卫请睁眼",
            GamePhase.DAY_START: "天亮了",
            GamePhase.SHERIFF_ELECTION: "警长竞选",
            GamePhase.DAY_DISCUSS: "自由讨论",
            GamePhase.DAY_VOTE: "投票环节",
        }
        return phase_titles.get(phase, str(phase))
    
    # === 流程主持 ===
    
    def determine_speaking_order(self, alive_ids: List[int], sheriff_id: Optional[int], dead_id: Optional[int] = None) -> List[int]:
        """
        决定发言顺序
        
        规则：
        - 警长存在时，由警长指定起始方向（这里简化为随机顺时针或逆时针）
        - 无警长时，随机指定
        - 警长最后发言（总结发言权）
        - 如果有死者（且不是第一天无遗言），死者可能先发言（遗言），但这里主要指日常讨论
        """
        if not alive_ids:
            return []
            
        sorted_ids = sorted(alive_ids)
        
        # Determine start index
        start_index = 0
        if sheriff_id and sheriff_id in sorted_ids:
            # Sheriff decides order. For MVP, we simulate sheriff deciding to start from left or right of dead player or random
            # Simplified: Random start
            start_index = random.randint(0, len(sorted_ids) - 1)
        else:
            start_index = random.randint(0, len(sorted_ids) - 1)
            
        # Clockwise order
        order = sorted_ids[start_index:] + sorted_ids[:start_index]
        
        # If sheriff exists, move sheriff to end
        if sheriff_id and sheriff_id in order:
            order.remove(sheriff_id)
            order.append(sheriff_id)
            
        return order
    
    def get_time_limit(self, phase: GamePhase) -> int:
        """
        获取阶段时间限制（秒）
        
        默认配置：
        - 发言: 60秒
        - 投票: 30秒
        - 狼人讨论每轮: 45秒
        - 技能使用: 30秒
        """
        if phase == GamePhase.DAY_DISCUSS:
            return 60
        elif phase in [GamePhase.DAY_VOTE, GamePhase.SHERIFF_VOTE, GamePhase.NIGHT_WOLF_VOTE]:
            return 30
        elif phase == GamePhase.NIGHT_WOLF_DISCUSS:
            return 45
        elif phase in [GamePhase.NIGHT_SEER, GamePhase.NIGHT_WITCH, GamePhase.NIGHT_GUARD, GamePhase.HUNTER_SKILL]:
            return 30
        return 60
