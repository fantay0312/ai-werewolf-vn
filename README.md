# 🐺 AI 狼人杀 (AI Werewolf VN)

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)
![Vue](https://img.shields.io/badge/vue-3.x-42b883.svg)
![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)

**一款基于大语言模型（LLM）驱动的单人狼人杀网页游戏**

*Player vs 11 AI Agents | Visual Novel Style | Immersive Deduction Experience*

</div>

---

## ✨ 核心特色

| 特性 | 描述 |
|------|------|
| 🎭 **AI 智能体** | 11名AI玩家拥有独立人格、记忆和推理能力，能够伪装、欺骗和逻辑分析 |
| 📖 **视觉小说风格** | 打字机效果、场景氛围切换，还原经典网文/VN阅读体验 |
| 🧠 **防幻觉系统** | 分层记忆架构（绝对事实层 + 历史摘要层 + 近期对话层） |
| 💬 **纯文字交互** | 所有交流、辩论、推理通过文字进行 |

## 🛠️ 技术栈

```
Frontend          Backend           Deploy
───────────────────────────────────────────
Vue 3             Python 3.10+      Docker
TypeScript        FastAPI           Docker Compose
Pinia             OpenAI SDK
TailwindCSS       Pydantic
```

## 🚀 快速开始

### 前置要求

- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- OpenAI 兼容的 API Key（OpenAI / OpenRouter / 其他兼容接口）

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/ai-werewolf-vn.git
cd ai-werewolf-vn
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
LLM_API_BASE=https://api.openai.com/v1   # 或 https://openrouter.ai/api/v1
LLM_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-4-turbo-preview            # 建议使用推理能力强的模型
```

### 3. 启动服务

```bash
docker-compose up --build
```

### 4. 开始游戏

| 服务 | 地址 |
|-----|------|
| 🎮 游戏前端 | http://localhost:8080 |
| 📚 API文档 | http://localhost:8000/docs |

---

## 🎲 游戏规则 (12人标准局)

### 好人阵营 (8人)

| 角色 | 数量 | 技能 |
|------|------|------|
| 村民 | 4 | 无特殊技能，靠推理投票 |
| 预言家 | 1 | 每晚查验一人身份（好人/坏人） |
| 女巫 | 1 | 一瓶解药 + 一瓶毒药 |
| 守卫 | 1 | 每晚守护一人免受狼人击杀 |
| 猎人 | 1 | 出局时可开枪带走一人 |

### 狼人阵营 (4人)

| 角色 | 数量 | 技能 |
|------|------|------|
| 狼人 | 3 | 每晚参与击杀讨论 |
| 狼王 | 1 | 出局时可开枪带走一人（被毒/自爆除外） |

---

## 📁 项目结构

```
ai-werewolf-vn/
├── backend/                 # FastAPI 后端服务
│   ├── app/
│   │   ├── ai/              # AI 智能体与 Prompt 构建
│   │   ├── core/            # 核心游戏逻辑 (GameManager, Judge)
│   │   ├── models/          # Pydantic 数据模型
│   │   └── routes/          # API 路由
│   ├── tests/               # 测试用例
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                # Vue 3 前端应用
│   ├── src/
│   │   ├── components/      # Vue 组件
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── views/           # 页面视图
│   │   └── api/             # API 调用封装
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml       # 容器编排配置
└── .env.example             # 环境变量模板
```

---

## 💻 本地开发

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

<div align="center">

**Made with ❤️ for Werewolf Game Enthusiasts**

</div>
