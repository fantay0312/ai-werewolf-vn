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

## 进行中

- 🔧 前端 Chunk 3 (Opus): index.css 千行清理、日/夜主题、1280px 响应式、Home 打磨

## 待办

- 终审: 全量验证 + /code-review + Codex 独立审查门 → 修复
- 浏览器可视化检查 (后端 8010 冒烟服务器仍在跑, 托管 dist)
- push + PR
