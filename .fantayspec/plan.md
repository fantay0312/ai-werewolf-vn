# 深度重构执行计划

生成: 2026-07-13 | 分支: refactor/deep-refactor | 依据: constraints.md (Codex 18 + Opus 101 发现, Fable 已核实)

## 编排原则

- **WS-A 后端** = Codex gpt-5.6-sol (resume session 019f5708-c0d7-72c0-aa84-180504aa63e1, 已有全库上下文)
  在隔离 worktree `.fantayspec/codex-out/wt` (分支 codex/backend-refactor) 直接编辑+跑测试, Fable diff 审查后合并
- **WS-B 前端** = Opus 子代理, 直接在主树 frontend/ 工作 (与 WS-A 零文件交集)
- 两工作流并行; SSE 契约先行定义, 双方照契约各自实现

## SSE 契约 (双方共同遵守)

- 新增 `POST /api/sse/ticket` (需 X-Player-Token 头): 返回 `{ticket, expires_in}` 短时效一次性票据
- `GET /api/sse/events?session_id=..&viewer_id=..&ticket=..` 接受票据作为 header 之外的替代认证
  (浏览器 EventSource 无法设置自定义头)
- 事件负载格式维持 EventPresenter.to_sse 现状; 前端以 event.name 分发, 收到事件后按需拉全量状态
  (增量事件驱动"何时刷新", 全量 GET 保证一致性 — 渐进式, 不要求一次做成纯事件溯源客户端)

## WS-A 后端 (Codex) — Pass 1: 正确性

1. 胜负判定统一: 每次死亡结算后 (夜晚/放逐/PK/开枪/自爆) 即查 check_win_condition, 短路进 GAME_END; 消除"幽灵夜晚"
2. GAME_END 终局处理器: 注册 handler, 发 PhaseChangeEvent + GameEndEvent 广播, 持久化终局快照 (盘活 events.py 死代码)
3. 首夜遗言可达: 修 day_start 门条件 (day 语义统一, 首个白天有遗言), 对齐 _get_pending_ai_players 的逐个发言窗口
4. 会话级动作锁: 人类 process_action 与 AI 路径共用 per-session 锁; LLM decide_action 移出临界区, 应用前重校验; 相位推进原子化
5. 发言相位卡死修复: AI+fallback 双失败时推进 speaker 指针而非仅 has_acted; 加无 pending actor 看门狗
6. 快照恢复后重启调度: lifespan startup 对每个恢复会话 trigger_ai_actions
7. Fallback 理性化: 女巫失败绝不随机毒人(PASS), 狼刀 fallback 优先非狼, 猎人 fallback 不开枪(PASS)
8. 被毒警长允许移交警徽 (标准规则, config 开关保留旧房规)

## WS-A 后端 (Codex) — Pass 2: 信息安全 + 架构

9. 投影泄露修复: 投票进行中不公开实时票型; 药/枪状态仅本人视角可见
10. SSE 强化: 每 viewer 队列封顶+溢出策略; ticket 认证端点 (见契约); 事件发布会话内序列化
11. AI 层单一事实源: 任务文本由 PHASE_PROMPT_CONTRACTS 生成 (消除 prompt_builder 漂移);
    memory_manager 保留 _runtime_meta; DeathRecord 记真实死亡 day/phase/cause
12. 指标基数修复: 未匹配路径归并固定 label
13. 去重重构: day_vote_result/day_pk_result 共享基类, 四个发言窗口 handler 提取公共 TurnWindow 基类
14. 全程新增/修订测试; 重点补集成流转测试 (首夜→遗言→白天全链)

## WS-B 前端 (Opus) — Chunk 1: 数据层

1. SSE 客户端替换 2s 轮询 (按上方契约; EventSource + 事件触发的按需全量刷新; 断线指数退避重连, 回退轮询)
2. 轮询/连接失败策略: 404 → 清 session 回首页; 连续失败 → 明确 UI, 停止骚扰服务器
3. 恢复死局修复: "正在恢复游戏"页加超时 + 重试/回首页按钮
4. store 错误通道接线: 全局 toast/banner 订阅 state.error (当前无任何组件消费!)
5. types 对齐后端模型, 清 any

## WS-B 前端 (Opus) — Chunk 2: 游戏页重构 + 修复

6. ErrorBoundary 包 GameRoom (白屏保护)
7. VoteModal PK 票修复: DAY_PK_VOTE 时候选人限定 pk_candidates
8. GameTable 交互接线: selectionMode 由 phase+role 推导, 座位点击直连 submitAction, current_speaker 高亮
9. GameRoom/ActionPanel 职责重划 (450 行 ActionPanel 拆分), 角色名/色/图标逻辑收敛到单一工具模块
10. 死亡玩家体验 + 终局画面 (承接后端 GAME_END 事件)

## WS-B 前端 (Opus) — Chunk 3: 视觉与 Home

11. index.css 1038 行清理: 死样式删除, 重复归并进 Tailwind theme, z-index/色彩 token 化
12. 日/夜氛围主题一致性 + 动画性能 (降 jank)
13. Home 页打磨 + 响应式 (1280px 可玩)
14. lint 清零 (含既有 DialogBox useEffect deps warning)

## 验证与收尾

- 每 chunk/pass 后: 后端 pytest 全绿 + 前端 tsc+vite build + eslint
- 合并 WS-A: Fable 逐文件 diff 审查 → merge codex/backend-refactor
- 终审: /code-review + Codex reviewer 独立门 (双模型审) → 修复
- README 重写 (React 19/Zustand 现实), docker-compose 校验
- push refactor/deep-refactor → GitHub, 开 PR
