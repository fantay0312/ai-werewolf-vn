"""
AI狼人杀游戏配置管理模块

集中管理所有游戏配置、LLM配置、阶段时间限制等参数
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class Environment(Enum):
    """运行环境"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class LLMConfig:
    """LLM配置"""
    api_key: str = ""
    api_base: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    retry_count: int = 3
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """从环境变量加载配置"""
        return cls(
            api_key=os.getenv("LLM_API_KEY", ""),
            api_base=os.getenv("LLM_API_BASE"),
            model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            retry_count=int(os.getenv("LLM_RETRY_COUNT", "3")),
            timeout=int(os.getenv("LLM_TIMEOUT", "30"))
        )


@dataclass
class GameRoleConfig:
    """游戏角色配置"""
    villagers: int = 4      # 村民数量
    wolves: int = 3         # 普通狼人数量
    wolf_king: int = 1      # 狼王数量
    seer: int = 1           # 预言家数量
    witch: int = 1          # 女巫数量
    guard: int = 1          # 守卫数量
    hunter: int = 1         # 猎人数量

    @property
    def total_players(self) -> int:
        """总玩家数"""
        return (
            self.villagers + self.wolves + self.wolf_king +
            self.seer + self.witch + self.guard + self.hunter
        )

    @property
    def wolf_count(self) -> int:
        """狼人总数"""
        return self.wolves + self.wolf_king

    @property
    def good_count(self) -> int:
        """好人总数"""
        return self.total_players - self.wolf_count

    def get_role_list(self) -> List[str]:
        """获取角色列表"""
        roles = []
        roles.extend(["villager"] * self.villagers)
        roles.extend(["wolf"] * self.wolves)
        roles.extend(["wolf_king"] * self.wolf_king)
        roles.extend(["seer"] * self.seer)
        roles.extend(["witch"] * self.witch)
        roles.extend(["guard"] * self.guard)
        roles.extend(["hunter"] * self.hunter)
        return roles


@dataclass
class PhaseTimeConfig:
    """阶段时间限制配置（秒）"""
    game_start: int = 30
    night_wolf_discuss: int = 45
    night_wolf_vote: int = 30
    night_seer: int = 30
    night_witch: int = 30
    night_guard: int = 30
    day_discuss: int = 60
    day_vote: int = 30
    day_last_words: int = 60
    sheriff_election: int = 30
    sheriff_speech: int = 60
    sheriff_vote: int = 30
    sheriff_transfer: int = 20
    hunter_skill: int = 20
    pk_speech: int = 60
    pk_vote: int = 30

    def get_time_limit(self, phase: str) -> int:
        """获取指定阶段的时间限制"""
        phase_map = {
            "GAME_START": self.game_start,
            "NIGHT_WOLF_DISCUSS": self.night_wolf_discuss,
            "NIGHT_WOLF_VOTE": self.night_wolf_vote,
            "NIGHT_SEER": self.night_seer,
            "NIGHT_WITCH": self.night_witch,
            "NIGHT_GUARD": self.night_guard,
            "DAY_DISCUSS": self.day_discuss,
            "DAY_VOTE": self.day_vote,
            "DAY_LAST_WORDS": self.day_last_words,
            "SHERIFF_ELECTION": self.sheriff_election,
            "SHERIFF_SPEECH": self.sheriff_speech,
            "SHERIFF_VOTE": self.sheriff_vote,
            "SHERIFF_TRANSFER": self.sheriff_transfer,
            "HUNTER_SKILL": self.hunter_skill,
            "DAY_PK_SPEECH": self.pk_speech,
            "DAY_PK_VOTE": self.pk_vote
        }
        return phase_map.get(phase, 60)


@dataclass
class MemoryConfig:
    """记忆系统配置"""
    # Token预算
    system_prompt_budget: int = 800
    character_budget: int = 300
    facts_budget: int = 1500
    summary_budget: int = 2500
    recent_budget: int = 2500
    task_budget: int = 400

    # 摘要设置
    summary_threshold_tokens: int = 3000  # 超过此阈值触发摘要
    summary_target_tokens: int = 1500     # 摘要后目标token数
    max_recent_dialogues: int = 20        # 最近对话最大条数

    @property
    def total_budget(self) -> int:
        """总Token预算"""
        return (
            self.system_prompt_budget + self.character_budget +
            self.facts_budget + self.summary_budget +
            self.recent_budget + self.task_budget
        )


@dataclass
class GameRulesConfig:
    """游戏规则配置"""
    # 基础规则
    has_sheriff: bool = True              # 是否有警长系统
    first_day_has_vote: bool = True       # 第一天白天是否有投票
    witch_can_self_save: bool = False     # 女巫能否自救（第一晚）
    witch_save_poison_same_night: bool = False  # 女巫能否同一晚使用解药和毒药
    guard_can_self_protect: bool = True   # 守卫能否自守
    guard_consecutive_protect: bool = False  # 守卫能否连续守护同一人

    # 同守同救规则
    guard_witch_same_target_die: bool = True  # 守卫和女巫同时保护同一人是否死亡

    # 狼王规则
    wolf_king_poison_can_shoot: bool = False  # 狼王被毒死能否开枪
    wolf_king_last_wolf_can_shoot: bool = False  # 狼王是最后一狼能否开枪
    wolf_king_self_explode_can_shoot: bool = False  # 狼王自爆能否开枪

    # 猎人规则
    hunter_poison_can_shoot: bool = False  # 猎人被毒死能否开枪

    # 警长规则
    sheriff_vote_weight: int = 2          # 警长投票权重
    sheriff_poison_transfer: bool = False  # 警长被毒死能否传递警徽

    # 投票规则
    tie_vote_no_execution: bool = True    # 平票是否无人出局
    pk_max_rounds: int = 2                # PK最大轮数


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    log_level: str = "INFO"
    allowed_origins: List[str] = field(default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"])
    game_cleanup_interval: int = 300       # 游戏清理间隔（秒）
    game_expire_time: int = 3600           # 游戏过期时间（秒）

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            reload=os.getenv("RELOAD", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            allowed_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
            game_cleanup_interval=int(os.getenv("GAME_CLEANUP_INTERVAL", "300")),
            game_expire_time=int(os.getenv("GAME_EXPIRE_TIME", "3600"))
        )


@dataclass
class Config:
    """主配置类"""
    env: Environment = Environment.DEVELOPMENT
    llm: LLMConfig = field(default_factory=LLMConfig)
    roles: GameRoleConfig = field(default_factory=GameRoleConfig)
    phase_times: PhaseTimeConfig = field(default_factory=PhaseTimeConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    rules: GameRulesConfig = field(default_factory=GameRulesConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def load(cls) -> "Config":
        """从环境变量加载完整配置"""
        env_str = os.getenv("ENV", "development").lower()
        env = Environment(env_str) if env_str in [e.value for e in Environment] else Environment.DEVELOPMENT

        return cls(
            env=env,
            llm=LLMConfig.from_env(),
            roles=GameRoleConfig(),
            phase_times=PhaseTimeConfig(),
            memory=MemoryConfig(),
            rules=GameRulesConfig(),
            server=ServerConfig.from_env()
        )


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config.load()
    return _config


def update_llm_config(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None
) -> LLMConfig:
    """动态更新LLM配置"""
    global _config
    if _config is None:
        _config = Config.load()

    llm = _config.llm
    if api_key is not None:
        llm.api_key = api_key
    if api_base is not None:
        llm.api_base = api_base if api_base else None
    if model is not None:
        llm.model = model
    if max_tokens is not None:
        llm.max_tokens = max_tokens
    if temperature is not None:
        llm.temperature = temperature

    return llm


# 便捷访问函数
def get_llm_config() -> LLMConfig:
    """获取LLM配置"""
    return get_config().llm


def get_role_config() -> GameRoleConfig:
    """获取角色配置"""
    return get_config().roles


def get_phase_time(phase: str) -> int:
    """获取指定阶段的时间限制"""
    return get_config().phase_times.get_time_limit(phase)


def get_rules() -> GameRulesConfig:
    """获取游戏规则配置"""
    return get_config().rules


def get_memory_config() -> MemoryConfig:
    """获取记忆系统配置"""
    return get_config().memory
