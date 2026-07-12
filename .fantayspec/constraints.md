# 约束集与审计发现 (research 阶段产出)

生成: 2026-07-12 | 分支: refactor/deep-refactor | 基线: 后端 116 tests 全绿, 前端 tsc+vite 构建通过

## 项目事实

- 后端: FastAPI, ~10k 行, 分层 (core/handlers ×18, application, domain, infrastructure, interfaces, ai)
- 前端: React 19 + Zustand + Tailwind v4 + Vite 8, ~5.5k 行 (pages/, components/game|common|ui, store)
- 遗留: frontend-vue/ (已 gitignore, 从未提交, 不再维护); README 仍写 Vue/Pinia — 需重写
- 资产: 已优化 37MB→1.5MB WebP, 文件名=角色 key
- 秘钥安全: rule/ 与 frontend-vue/ 均 gitignored 且从未进 git 历史, 可安全推送
- 远端: git@github.com:fantay0312/ai-werewolf-vn.git; 用户规范: 不直接提交 main, refactor/* 分支

## Codex 审计 (gpt-5.6-sol analyzer, 交叉验证源 A)

总评: 核心规则基本正确, 但存在可破坏对局结果的并发/警徽/首夜遗言缺陷; 状态机缺超时恢复与可靠终局。安全深度重构可行性 6/10。

### HIGH
1. `game_manager.py:365` 玩家操作无会话锁 — 并发请求可重复行动 (女巫同夜双药) → 会话事务锁包围校验+转移
2. `game_manager.py:467` time_remaining 仅赋值, 无超时动作 — 断线永久卡局 → 持久化截止时间+自动弃权
3. `game_manager.py:217` 快照恢复后不重启 AI 调度/阶段推进 → 恢复时重建阶段任务
4. `handlers/night_resolve.py:99` 结算先递增 day, 首夜遗言条件永不成立 → 统一夜/昼编号语义
5. `game_manager.py:122` GAME_END 无 handler, 终局不广播不持久化 → 显式终局处理器
6. `handlers/night_wolf_vote.py:44` 狼刀允许选狼人/狼王 → 目标限定非狼存活玩家
7. `handlers/night_resolve.py:21` 被毒警长强制丢徽, 绕过移交流程 → 死亡原因统一进移交

### MED
8. `handlers/sheriff_vote.py:140` 警长平票直接无警长, 无 PK 复投
9. `handlers/day_start.py:19` 胜负仅天亮检查, 白天屠边后仍执行夜晚 → 死亡链结算后即查
10. `handlers/night_witch.py:60` 女巫任意夜无限自救 → 规则配置化
11. `rules.py:91` 最后一只狼王死亡被禁开枪 (超出毒杀限制) → 移除数量限制
12. `projections/public_view_projector.py:45` 投票进行中泄露实时票型 → 结算前隐藏
13. `projections/public_view_projector.py:23` 公开药/枪状态泄露身份 → 仅本人可见
14. `event_manager.py:81` SSE 队列无界 → 容量+溢出策略
15. `game_manager.py:735` 事件独立任务发布, 跨发布者顺序不定 → 会话序列化出口

### LOW
16. `domain/services/command_validator.py:12` 验证器拒绝预言家 PASS 但 handler 支持
17. `rules.py:19` 胜负固定屠边且同灭判好人赢 → 策略配置化
18. `game_manager.py:805` 每行动全量重写快照 → 批量+增量

### Codex 重构目标
- 提取 SessionTransaction (锁+校验+转移+事件+持久化)
- 提取 RulePolicy (女巫/守卫/开枪/胜负语义)
- 合并三种投票为 VoteEngine
- 合并讨论/竞选/PK/遗言为 TurnWindowHandler
- 可恢复 deadline 调度器 + 终局处理器

## Fable 独立验证 (对 Codex 发现的核查)

- ✅ **F4 实锤且升级**: 模拟实证 (scratchpad/sim_first_night.py): 首夜后 day=2, day_start→DAY_DISCUSS。
  **警长竞选 + 首夜遗言在真实对局中从未触发** (day_start.py:70,76 的 `day == 1` 永不成立;
  pending_sheriff_election 仅自爆逻辑设置)。116 个测试全是手工构造状态, 掩盖集成断裂。最高优先级修复。
- ✅ F5 确认: PHASE_HANDLERS 无 GAME_END; _advance_phase 中 publish/persist 全在 `if handler:` 内 →
  终局不广播 SSE、不持久化、无 on_enter。
- ✅ F3 确认: restore_persisted_games 仅载状态; import 时构造 GameManager (无事件循环), 恢复后无人调
  trigger_ai_actions → 轮到 AI 行动的恢复局永久冻结。修复点在 lifespan startup。
- ⚠️ F1 降级为 MED: 单 worker asyncio 下 validate+process_action 同步块内原子; 但 _advance_phase 的
  await 间隙 + trigger_ai_actions create_task 交错仍可产生阶段边界竞态。会话锁仍值得做。
- ❌ F6 驳回: 狼人"自刀"是标准规则合法战术, 不禁止。但 fallback 应避免随机刀狼 (见下)。
- ⚠️ F7 属规则取向: "被毒警徽流失"是作者注释明示的房规; 标准规则允许移交。改为标准规则并可配置。
- ✅ F2/F9/F10/F11/F12/F13/F14/F15/F16/F17/F18 代码层面确认存在。

## Fable 新增发现 (Codex 未报)

- 🔴 `game_manager.py:103` PORTRAIT_MAP + `_init_players:339` fallback 仍指向旧中文文件名图片
  (已改名 webp) → 后端下发的 portrait 字段全部 404。必须同步改为 /images/portraits/<role>.webp。
- 🔴 `game_manager.py:767` 女巫 fallback: LLM 失败时会**随机毒人** → 应 PASS。
- 🟡 `game_manager.py:761` 狼 fallback 目标含狼队友 (随机自刀不合理) → 优先非狼目标。
- 🟡 `game_manager.py:790` 猎人 fallback 随机开枪带走一人 → 应 PASS (不开枪) 更安全。
- 🟡 `rules.py:20` 胜负未含"狼人数≥好人数"即胜的常见规则 (低优先级, 屠边规则下影响小)。

## Opus 七域审计 (交叉验证源 B) — 101 issues, 明细见 scratchpad/audit_results.json

**修正 Fable 前述结论**: 警长竞选并未断——真实流程为 GAME_START → SHERIFF_ELECTION → NIGHT_START
(竞选在首夜前, 房规顺序, 功能正常)。day_start 里 `day==1` 竞选分支只是死代码。首夜遗言不可达维持成立。

### HIGH 汇总 (去重后)
- 后端核心: 白天死亡(放逐/PK/开枪/自爆)不查胜负 → 已定胜负仍跑完整"幽灵夜晚"; 首夜遗言不可达;
  AI 双失败卡死发言窗口 (speaker 指针不推进 → 永久卡局); GAME_END 无 handler (=Codex F5)
- 后端 AI: memory_manager.save_to_player 丢 _runtime_meta → 相位变更检测失效; DeathRecord 记当前
  day/phase 而非真实死亡时刻 (绝对事实层污染); prompt_builder 与 PHASE_PROMPT_CONTRACTS 双份相位契约已漂移
- 后端 infra: metrics 路径 label 无界基数 (SPA catch-all 任意 URL 都建 histogram 序列)
- SSE 断层 (双审计员一致): 后端完整 SSE 管道存在但前端零消费, 2s 全量轮询; 且浏览器 EventSource
  无法带 X-Player-Token 头 → 私有流对浏览器不可达 (需 ticket 查询参数)
- 前端: store.error 无任何组件消费 (所有错误静默); 轮询无失败策略 (404 后每 2s 打服务器到永远);
  恢复页无超时死局; 无 ErrorBoundary (白屏); VoteModal PK 票不限 pk_candidates (可投非 PK 者);
  GameTable 满套交互 API 零接线 (点座位/高亮全失效)
- 样式: 19 issues 全 MED/LOW (死样式/重复/token 化), 无 HIGH

### 处置
全部纳入 plan.md 工作流 (WS-A Pass1/2, WS-B Chunk1/2/3); Codex F6 (狼自刀) 驳回不修;
F11 (末狼狼王枪) 降级暂缓。
