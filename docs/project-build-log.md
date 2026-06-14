# 小红书 AI 二创工作台搭建记录

这份文档记录小红书 AI 二创工作台从想法到 MVP 的搭建过程，方便以后迁移项目、复盘产品设计，或把项目整理到作品集/简历中。

## 1. 项目起点

最初目标是做一个本地工具：通过 OpenCLI 获取小红书上某个关键词的帖子正文和图片，例如“北京美食”，再用 AI 根据不同人设进行二创。

核心需求包括：

- 用户可以输入关键词和采集数量。
- 系统通过 OpenCLI 获取小红书笔记的标题、作者、正文、互动数据和图片。
- 用户可以创建不同人设，例如“小白”：00 后女大学生，语言生动活泼。
- 用户选择某个人设后，AI 基于原帖正文生成新的小红书风格草稿。
- 用户可以编辑 AI 初稿，并保存终稿。
- 系统可以从 AI 初稿和用户终稿的差异中提炼风格规则，反哺该人设后续生成。

这个项目的重点不是自动发布，而是搭建一个“采集素材 -> 选择人设 -> AI 二创 -> 人工编辑 -> 风格规则沉淀 -> 本地导出”的内容生产工作流。

## 2. 技术方案

项目采用本地优先的前后端结构：

- 后端：FastAPI
- 数据库：SQLite
- 前端：Vite + React
- 内容采集：OpenCLI
- AI 生成：MiniMax / OpenAI-compatible API
- 图片存储：本地 `data/images/`
- 草稿导出：本地 `exports/`

主要目录：

```text
xiaohongshu-remix-studio/
├── backend/          # FastAPI 后端
├── frontend/         # React 工作台
├── data/             # SQLite 数据库和本地图片，未提交到 GitHub
├── docs/             # 公开展示页和项目文档
└── .codex/skills/    # 项目协作 skill
```

## 3. 数据模型

后端使用 SQLite 保存本地数据，核心表包括：

- `notes`：采集到的小红书笔记，包括关键词、标题、作者、正文、点赞、收藏、评论、链接、状态和错误信息。
- `note_images`：笔记图片的本地路径、排序和文件大小。
- `personas`：人设名称和描述。
- `persona_rules`：每个人设沉淀出的写作规则。
- `drafts`：AI 生成稿、用户终稿、建议标签、图片建议和状态。
- `edit_events`：AI 初稿与用户终稿之间的差异记录。

默认人设：

```text
小白：00后女大学生，语言生动活泼，喜欢用真实体验、轻松吐槽和口语化表达分享好吃好玩的东西。
```

后来又加入了“小黑”等人设，用于展示不同口吻的二创效果。

## 4. OpenCLI 采集流程

后端通过 `backend/app/opencli_client.py` 封装 OpenCLI 调用：

```text
opencli xiaohongshu search <keyword> --limit <count>
opencli xiaohongshu note <url>
opencli xiaohongshu download <url> --output data/images
```

实现上使用 `subprocess.run([...])` 参数数组调用，避免 shell 注入风险。

采集接口位于 `backend/app/main.py` 的 `/api/collect`。

实际容错逻辑：

- 如果搜索阶段整体失败，接口直接返回错误。
- 如果搜索成功后，某条笔记详情失败，该条会标记为 `failed`，继续处理其他候选素材。
- 如果详情成功但图片下载失败，该条会标记为 `partial`，正文仍可入库。
- 成功、失败和部分成功的笔记都会带状态写入数据库。

因此更准确的产品表述是：

```text
搜索拿到候选素材后，单条详情或图片下载失败会被标记状态，其他素材仍可继续入库。
```

## 5. AI 生成流程

AI 服务位于 `backend/app/ai_service.py`。

MiniMax 通过 OpenAI-compatible Chat Completions 接入：

```python
OpenAI(api_key=key, base_url="https://api.minimaxi.com/v1")
client.chat.completions.create(model="MiniMax-M2.7", messages=[...])
```

`.env` 中的关键配置：

```env
AI_PROVIDER=minimax
MINIMAX_API_KEY=你的 Token Plan Key
MINIMAX_MODEL=MiniMax-M2.7
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MOCK_AI=false
OPENCLI_BIN=opencli
```

MiniMax 当前只用于文字二创和规则提炼，不做图片生成，也没有把图片传给模型做图像理解。

生成接口会要求模型返回 JSON：

```json
{
  "title": "改写标题",
  "body": "改写正文",
  "tags": ["标签1", "标签2"],
  "image_advice": "图片使用建议"
}
```

如果没有 API Key、Key 无效、模型返回非 JSON 或字段缺失，后端会转换成可读错误，前端在二创区域展示。

## 6. 人设和规则沉淀

项目里人设不是一次性 prompt，而是一个可以持续维护的写作配置。

用户可以：

- 新建人设。
- 编辑人设名称和描述。
- 手动添加或删除风格规则。
- 根据 AI 初稿和用户终稿的差异提炼候选规则。
- 确认规则后写入该人设，后续生成自动携带。

例如，如果“小白”生成的标题太频繁使用“救命”，更推荐在人设规则中添加：

```text
标题要有小白的活泼感，但不要总用“救命”开头；多用场景、反差、真实感和馋感来制造吸引力。
```

这类偏好应该写入 `persona_rules`，而不是改全局生成 prompt。

## 7. 前端工作台迭代

前端最初是基础工作台，后来围绕真实使用体验进行了多轮优化。

最终主要布局：

- 顶部：状态和采集区。
- 第一行：横向人设系统。
- 第二行：三列工作台。
  - 左侧：已采集素材。
  - 中间：原文 vs 二创，上下对照。
  - 右侧：草稿箱。

关键交互：

- 点击素材后，中间展示对应原文和图片。
- 点击草稿箱中的草稿后，会同步选中对应原帖和人设。
- 原文图片也会显示到二创区域，方便导出时保持图文对应。
- 用户可以复制 Markdown。
- 用户可以把草稿和图片保存到本地。
- 保存成功后前端会提示导出位置。

图片顺序曾经出现过反转问题，后来在后端展示排序逻辑中修正。后续改图片逻辑时要特别注意：小红书原帖第一张图应在工作台里排第一。

## 8. 静态 Demo 展示页

为了更适合公开分享和作品集展示，项目新增了静态 Demo 页面：

```text
docs/index.html
docs/styles.css
docs/script.js
```

这个页面不连接后端、不调用 OpenCLI、不请求 AI API，只用虚拟数据展示产品用途和主要交互。

展示页包括：

- 项目定位。
- 内容二创工作流。
- 采集概览。
- 人设系统。
- 已采集素材。
- 原文 vs 二创。
- 草稿箱。
- 架构说明。
- MVP 版本的关键产品取舍。
- 适用内容生产场景。

GitHub Pages 可以从 `main` 分支的 `/docs` 目录发布，公开链接形态为：

```text
https://otrttf.github.io/xhs-remix-studio/
```

## 9. Git 和 GitHub 经验

项目使用 GitHub 管理版本：

```text
git status
git add .
git commit -m "提交说明"
git push
```

本项目曾经遇到 `ahead 1, behind 1`，原因是：

- 旧版 demo 页面已经推送到 GitHub。
- 本地继续用 `git commit --amend` 改写了同一个提交。
- Git 认为本地新版和远端旧版是从同一个父提交分叉出来的两个提交。

经验：

- 已经 push 过的提交，后续尽量不要再 `commit --amend`。
- 如果还没 push，`amend` 可以用来整理最近一次提交。
- 如果已经 push 后又 amend，需要明确知道是否要用 `git push --force-with-lease`。

## 10. 迁移项目注意事项

可以把整个 `xiaohongshu-remix-studio/` 文件夹移动到新的目录，但要整体移动，不要拆开移动子目录。

建议一起保留：

- `.git`
- `.env`
- `.codex/`
- `backend/`
- `frontend/`
- `data/`
- `docs/`

移动后需要检查：

- `.codex/skills/xiaohongshu-remix-studio/SKILL.md` 中是否还有旧绝对路径。
- `backend/.venv` 是否还能正常工作。
- 前端 `npm run dev` 是否还能启动。

如果 `backend/.venv` 因为路径变化失效，可以重建：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## 11. 当前定位

这个项目最适合被描述为：

```text
一个面向内容运营/探店创作者的本地 AI 内容二创工作台，打通 OpenCLI 素材采集、MiniMax 文本二创、人设配置、人工编辑、风格规则沉淀和本地导出流程。
```

它的价值不只是“调用 AI 写文案”，而是把 AI 放进一个完整的内容生产工作流里，让用户的每一次编辑都能变成后续生成的风格资产。

## 12. 迁移后的维护记录

项目移动到 `/Users/hejiaxuan/Desktop/codexproject/xiaohongshu-remix-studio` 后，做了一次轻量体检：

- `backend/.venv/bin/python -m py_compile ...` 通过。
- `backend/.venv/bin/python backend/tests_smoke.py` 通过。
- `cd frontend && /usr/local/bin/npm run build` 通过。

本次维护修正了两处容易复发的问题：

- 图片展示顺序不再把排序后的第一张图片挪到末尾；小红书原帖第一张图会继续排在工作台第一位。
- MiniMax 默认 Base URL 调整为 `https://api.minimaxi.com/v1`，并让 `Settings` 在实例初始化时读取环境变量，方便测试或重启后拿到最新配置。

同时新增了 smoke test 覆盖图片顺序和 MiniMax 默认配置，后续改图片逻辑或 AI 配置时建议先跑验证命令。
