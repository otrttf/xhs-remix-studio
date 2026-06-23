# 小红书 AI 二创工作台

本地项目，用 `opencli` 抓取小红书关键词内容和图片，再用 MiniMax/OpenAI-compatible API 按人设生成二创草稿。用户编辑后的终稿会留下编辑记录，并可提炼为人设风格规则。

## 在线 Demo

```text
https://otrttf.github.io/xhs-remix-studio/
```

说明：这个链接是静态展示页，不会在线采集小红书内容，也不会调用 MiniMax/OpenAI API。

## 功能

- 关键词采集：输入 `北京美食` 等关键词，抓取标题、作者、正文、点赞、图片。
- 素材库：本地查看原帖正文和图片。
- 人设管理：创建人设、维护风格规则。
- AI 二创：选择素材和人设，生成标题、正文、标签、图片建议。
- 草稿库：保存终稿版本，复制 Markdown。
- 风格沉淀：从 AI 初稿和用户终稿的差异中提炼候选规则，确认后写入人设。

## 目录

```text
xiaohongshu-remix-studio/
├── backend/          # FastAPI + SQLite
├── frontend/         # Vite + React
├── data/app.db       # 自动生成
└── data/images/      # opencli 下载图片
```

## 准备

复制环境变量：

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=你的 OpenAI API Key
OPENAI_MODEL=gpt-5.4-mini
OPENCLI_BIN=opencli
```

如果使用 MiniMax，把 `.env` 改成：

```bash
AI_PROVIDER=minimax
MINIMAX_API_KEY=你的 MiniMax API Key
MINIMAX_MODEL=MiniMax-M2.7
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
OPENCLI_BIN=opencli
```

MiniMax 官方说明里，国际区常用 `https://api.minimax.io/v1`，中国区常用 `https://api.minimaxi.com/v1`。如果一个报 401，可以切换另一个后重启后端。

测试 MiniMax Key：

```bash
cd xiaohongshu-remix-studio/backend
source .venv/bin/activate
python check_ai.py
```

如果暂时不想调用真实模型，可以先用模拟模式体验流程：

```bash
MOCK_AI=true
```

如果 `opencli` 不在当前 shell 的 PATH 里，把 `OPENCLI_BIN` 改成完整路径，例如：

```bash
OPENCLI_BIN=/usr/local/bin/opencli
```

## 启动后端

```bash
cd xiaohongshu-remix-studio/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

后端地址：`http://127.0.0.1:8000`

如 8000 端口被占用，可临时指定：

```bash
PORT=8010 python run.py
```

检查状态：

```bash
curl http://127.0.0.1:8000/api/health
```

## 启动前端

当前机器如果 `npm` 可用：

```bash
cd xiaohongshu-remix-studio/frontend
npm install
npm run dev
```

前端地址：`http://127.0.0.1:5173`

如果你的 shell 提示 `npm: command not found`，需要先修复 Node/npm 安装或 PATH。当前环境能找到 `node`，但没有找到 `npm`。

## 使用流程

1. 打开前端，确认顶部没有 `opencli` 配置错误。
2. 在采集区输入关键词和数量，例如 `北京美食`、`10`。
3. 在素材库选择一条笔记。
4. 选择或创建人设，例如默认的“小白”。
5. 点击“生成”，得到 AI 草稿。
6. 编辑标题和正文，点击“保存终稿”。
7. 点击“提炼规则”，选择满意的候选规则加入人设。
8. 下一次生成会自动带上该人设已有规则。

## 说明

- 第一版只做本地草稿，不自动发布到小红书。
- 图片来自 `opencli xiaohongshu download` 下载的原帖图片。
- 单条笔记被风控或下载失败时会标记为失败/部分成功，不中断整批采集。
