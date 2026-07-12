# 🐺 AI 狼人杀 (AI Werewolf VN)

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)
![React](https://img.shields.io/badge/react-19-61dafb.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.x-3178c6.svg)
![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)

**一款基于大语言模型（LLM）驱动的单人狼人杀网页游戏**

*Player vs 11 AI Agents | Visual Novel Style | Immersive Deduction Experience*

</div>

---

## ✨ 核心特色

| 特性 | 描述 |
|------|------|
| 🎭 **AI 智能体** | 11 名 AI 玩家拥有独立人格、记忆和推理能力，能够伪装、欺骗和逻辑分析 |
| 📖 **视觉小说风格** | 打字机效果、日/夜场景氛围切换、角色立绘，还原经典 VN 阅读体验 |
| 🧠 **防幻觉系统** | 分层记忆架构（绝对事实层 + 历史摘要层 + 近期对话层）+ 响应合法性守卫 |
| ⚡ **实时事件流** | SSE 增量推送（按观战者隔离私有信息），断线自动重连、降级轮询 |
| 🎬 **回放与评估** | 领域事件驱动的对局回放 API 与 AI 决策质量评估报告 |
| 🛡️ **工程化后端** | 会话快照持久化、限流、Prometheus 指标、请求追踪、标准错误封装 |

## 🛠️ 技术栈

```
Frontend                Backend               Deploy
─────────────────────────────────────────────────────
React 19                Python 3.10+          Docker
TypeScript              FastAPI               Docker Compose
Zustand                 Pydantic              Nginx
TailwindCSS v4          OpenAI SDK
Vite 8
```

## 🚀 快速开始

### 前置要求

- [Docker](https://www.docker.com/) & Docker Compose
- OpenAI 兼容的 API Key（OpenAI / OpenRouter / 其他兼容接口）

### 1. 克隆仓库

```bash
git clone https://github.com/fantay0312/ai-werewolf-vn.git
cd ai-werewolf-vn
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```env
LLM_API_BASE=https://api.openai.com/v1   # 或其他兼容网关
LLM_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-4o                          # 建议使用推理能力强的模型
ADMIN_TOKEN=一串足够长的随机字符串          # 保护 /api/config 管理接口（compose 必填）
```

### 3. 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
|-----|------|
| 🎮 游戏前端 | http://localhost:8080 |
| 📚 API 文档 | http://localhost:8000/docs |
| ❤️ 健康检查 | http://localhost:8000/health |

---

## 🎲 游戏规则（12 人标准局）

### 好人阵营（8 人）

| 角色 | 数量 | 技能 |
|------|------|------|
| 村民 | 4 | 无特殊技能，靠推理投票 |
| 预言家 | 1 | 每晚查验一人身份（好人/狼人） |
| 女巫 | 1 | 一瓶解药 + 一瓶毒药 |
| 守卫 | 1 | 每晚守护一人免受狼人击杀，不可连续两晚守同一人 |
| 猎人 | 1 | 出局时可开枪带走一人（被毒除外） |

### 狼人阵营（4 人）

| 角色 | 数量 | 技能 |
|------|------|------|
| 狼人 | 3 | 每晚讨论并投票击杀目标 |
| 狼王 | 1 | 出局时可开枪带走一人（被毒/自爆除外） |

另含警长竞选（警长投票双倍权重）、警徽移交、平票 PK、遗言等标准流程。
胜负采用屠边规则：狼人全灭好人胜；神职或平民任一阵营全灭狼人胜。

---

## 📁 项目结构

```
ai-werewolf-vn/
├── backend/                     # FastAPI 后端
│   ├── main.py                  # 入口：中间件、限流、指标、SPA 托管
│   ├── app/
│   │   ├── core/                # 游戏引擎：GameManager + 21 个阶段处理器
│   │   ├── ai/                  # AI 智能体、Prompt 构建、分层记忆
│   │   ├── application/         # 应用层：AI 契约、投影、回放/评估服务
│   │   ├── domain/              # 领域事件、命令、阶段校验
│   │   ├── infrastructure/      # 快照存储、限流器、运行时指标
│   │   ├── interfaces/          # SSE 事件呈现
│   │   ├── models/              # Pydantic 模型
│   │   └── routes/              # API 路由 (game / player / sse / config)
│   └── tests/                   # pytest 测试套件
│
├── frontend/                    # React 19 前端
│   ├── src/
│   │   ├── pages/               # Home / GameRoom
│   │   ├── components/          # game / common / ui 组件
│   │   ├── store/               # Zustand 状态管理
│   │   ├── api/                 # API 客户端 + SSE 连接管理
│   │   └── types/               # TypeScript 类型
│   ├── public/images/           # WebP 游戏美术资产
│   ├── Dockerfile
│   └── nginx.conf               # 静态托管 + API/SSE 代理
│
├── docker-compose.yml
└── .env.example
```

---

## 💻 本地开发

### 后端（默认端口 8000）

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# 运行测试
python -m pytest tests -q
```

### 前端（默认端口 5173）

```bash
cd frontend
npm install
npm run dev     # 开发服务器
npm run build   # 生产构建（backend 可直接托管 dist/）
npm run lint
```

> 生产模式下后端会自动托管 `frontend/dist`，也可用 nginx 独立部署前端。

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支（`git checkout -b feature/AmazingFeature`）
3. 提交更改（`git commit -m 'feat: add amazing feature'`）
4. 推送到分支（`git push origin feature/AmazingFeature`）
5. 提交 Pull Request

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

<div align="center">

**Made with ❤️ for Werewolf Game Enthusiasts**

</div>
