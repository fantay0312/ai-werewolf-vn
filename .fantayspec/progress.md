# 重构进度

更新: 2026-07-13

## 已完成 (全部已合入 refactor/deep-refactor)

- ✅ WIP 检查点 + 资产优化 (37MB→1.5MB WebP, 文件名=角色 key, 前后端路径同步)
- ✅ 研究: Codex 18 发现 + Opus 7 域 101 发现, Fable 独立核实/裁决 (constraints.md)
- ✅ 后端 Pass 1 (Codex gpt-5.6-sol): 胜负判定统一(消灭幽灵夜晚)、GAME_END 终局处理器、
  首夜遗言可达(last_resolved_night)、会话锁+锁外 LLM 决策+过期丢弃、发言窗口卡死修复、
  快照恢复重启调度、fallback 理性化(女巫不再随机毒人)、被毒警长可移交(房规开关)、
  SSE ticket 认证+队列背压+无名事件。116→141 tests
- ✅ 后端 Pass 2 (Codex): projection_policy 单点信息策略(投票/药枪/死亡身份收敛)、
  memory _runtime_meta 保留、死亡事实真实记录、prompt 契约单一事实源、
  三大处理器基类去重(净-648行)、metrics 基数修复。141→174 tests
- ✅ 前端 Chunk 1 (Opus): SSE 实时层+轮询降级、统一失败策略、恢复超时逃生、
  全局 Toast、API base 修正(8001→8000/同源)
- ✅ 前端 Chunk 2 (Opus): ErrorBoundary、GameTable 交互接线、ActionPanel 配置化拆分、
  PK 票限定、roles/phases 库收敛、死亡旁观+终局翻牌、A11y/性能、
  .gitignore lib/ 陷阱修复(utils.ts 从未入库!)
- ✅ 部署链: React 前端 Dockerfile+nginx(SSE 代理), compose 修复; README 重写; MIT LICENSE
- ✅ 端到端冒烟: 无 LLM 全 fallback 跑通 建局→竞选→首夜→遗言→讨论;
  SSE 票据一次性验证; 状态响应零泄露

## 已收尾 (2026-07-13)

- ✅ 前端 Chunk 3: index.css 1038→817, 设计 token, 日/夜交叉淡入, reduced-motion, Home 防双击
- ✅ 双模型终审: /code-review (35 agent) + Codex 审查门 → 25 条实锤 (含 3 处真人死锁、
  立绘 URL 泄露身份、死亡技能晚于胜负判定、SSE 心跳误判) → 全部修复, 零误报
- ✅ 终态: 后端 188 tests 全绿, 前端 build+lint 0/0, 浏览器实测通过
- ✅ 推送: refactor/deep-refactor → GitHub, PR #2 (https://github.com/fantay0312/ai-werewolf-vn/pull/2)

## E2E 审计修复轮 (2026-08-31, fix/exile-lastwords-badge-wolfround)

浏览器完整实测两局（村民局+狼人局）+ replay 领域事件审计，发现并修复 3 个后端 bug + 1 个前端 UX：

- ✅ P0 `wolf_discuss_round` delattr 陷阱: night_wolf_discuss 用 delattr 删 pydantic 字段,
  之后整局所有狼人 AI 决策构建上下文抛 AttributeError 跌落 fallback（真实 LLM 局狼人策略全废）。
  改为归零重置 + NIGHT_START 统一清场。实测: 修复前一局 57 次错误 → 修复后 0
- ✅ P1 死亡警长警徽卡死: _get_fallback_action 无 SHERIFF_TRANSFER 分支 → AI 警长 fallback
  PASS 被拒 → force-skip 跳过但警徽留在尸体上, 之后每次死亡结算重复触发移交提示。
  修复: fallback 撕警徽 (VOTE target 0) + try_advance 兜底收敛
- ✅ P1 被放逐玩家无遗言: 放逐后直接入夜/技能。新增 next_phase_after_last_words 路由:
  放逐 → DAY_LAST_WORDS → 死亡技能链 → 夜晚。浏览器实测两次放逐遗言正常
- ✅ 前端警徽移交目标从裸数字输入框改为存活玩家下拉框
- ✅ 终态: 后端 196 tests 全绿 (190→196), 前端 build+lint 0/0, 浏览器两局完整实测通过
