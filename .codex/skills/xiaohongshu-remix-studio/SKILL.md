---
name: xiaohongshu-remix-studio
description: Use when working on this local Xiaohongshu remix studio: OpenCLI collection, SQLite notes/images, FastAPI backend, React frontend, MiniMax/OpenAI text rewriting, persona rules, draft editing, and style-rule refinement.
---

# Xiaohongshu Remix Studio

This skill captures the project-specific workflow for the local Xiaohongshu AI remix studio in `xiaohongshu-remix-studio/`.

## Project Intent

Build and maintain a local MVP that:

- Uses `opencli xiaohongshu` to collect posts for a keyword such as `北京美食`.
- Stores post text, metadata, and downloaded images locally.
- Lets the user choose a persona such as `小白`.
- Generates rewritten Xiaohongshu-style posts through an LLM.
- Saves user edits and distills edit patterns into reusable persona rules.

Do not add auto-publishing in v1. This is a local drafting and style-learning tool.

## Stack

- Backend: FastAPI + SQLite in `backend/`.
- Frontend: Vite + React in `frontend/`.
- Database: `data/app.db`.
- Images: `data/images/{note_key}/`.
- AI provider: configurable through `.env`.

Important commands:

```bash
cd backend
source .venv/bin/activate
python run.py
```

```bash
cd frontend
/usr/local/bin/npm run dev
```

Validation:

```bash
backend/.venv/bin/python -m py_compile backend/app/*.py backend/run.py backend/tests_smoke.py backend/check_ai.py
backend/.venv/bin/python backend/tests_smoke.py
cd frontend && /usr/local/bin/npm run build
```

## Configuration Rules

Use `.env` at the project root. The backend reads this file on startup, so restart the backend after any change.

MiniMax Token Plan configuration:

```bash
AI_PROVIDER=minimax
MINIMAX_API_KEY=<token-plan-key>
MINIMAX_MODEL=MiniMax-M2.7
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MOCK_AI=false
OPENCLI_BIN=opencli
```

OpenAI configuration:

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=<openai-key>
OPENAI_MODEL=gpt-5.4-mini
MOCK_AI=false
OPENCLI_BIN=opencli
```

Debug mode:

```bash
MOCK_AI=true
```

Use `backend/check_ai.py` to test MiniMax before debugging the UI:

```bash
cd backend
source .venv/bin/activate
python check_ai.py
```

If MiniMax returns `401 invalid api key (2049)`, first check that the key is a Token Plan Key and that `MINIMAX_BASE_URL=https://api.minimaxi.com/v1`. This issue is authentication, not image capability.

## Backend Patterns

Key files:

- `backend/app/main.py`: FastAPI routes.
- `backend/app/opencli_client.py`: OpenCLI subprocess wrapper.
- `backend/app/ai_service.py`: OpenAI/MiniMax provider abstraction.
- `backend/app/database.py`: SQLite schema and default persona.

Rules:

- Call `opencli` with argument arrays, not shell strings.
- Keep `OPENCLI_BIN` configurable because PATH can differ between terminals and Codex.
- `opencli xiaohongshu note` requires a full signed URL, not just note ID.
- `opencli xiaohongshu download` writes media into a note-keyed folder.
- Single-note OpenCLI failures should mark that note failed/partial and should not abort the entire batch.
- Convert model/provider errors into `AIServiceError` so the frontend gets readable 400 responses, not 500 tracebacks.
- Strip accidental quotes or `Bearer ` prefixes from API keys before creating the client.

MiniMax uses OpenAI-compatible Chat Completions:

```python
OpenAI(api_key=key, base_url="https://api.minimaxi.com/v1")
client.chat.completions.create(model="MiniMax-M2.7", messages=[...])
```

Current MiniMax usage is text-only. The app displays and exports Xiaohongshu images, but it does not currently send images to MiniMax for image understanding or generation.

OpenAI uses Responses API:

```python
client.responses.create(model=settings.openai_model, input=[...])
```

For generation, require JSON with:

- `title`
- `body`
- `tags`
- `image_advice`

Prompt locations:

- Main rewrite prompt: `backend/app/ai_service.py`, `AIService.generate()`.
- Style-rule extraction prompt: `backend/app/ai_service.py`, `AIService.suggest_rules()`.
- Persona-specific writing preferences should go into `persona_rules`, not the global prompt. Example: if `小白` titles overuse `救命`, add a rule such as `标题要保持小白的活泼感，但不要总用“救命”开头；多用场景、反差、真实感和馋感来制造吸引力。`

## Frontend Patterns

Key files:

- `frontend/src/main.jsx`: App UI and workflow.
- `frontend/src/api.js`: API client.
- `frontend/src/styles.css`: Layout and interaction styling.

UX expectations:

- Show API/backend errors inline, especially in the remix panel.
- Always show selected source note and selected persona before generation.
- Current layout:
  - Persona management is a horizontal full-width row.
  - Main work row has three columns: collected materials, original-vs-remix comparison, and draft library.
  - Original and remix content are vertically stacked in the middle column for easier comparison.
  - Clicking a draft in the draft library must also select its source note and persona so the original post appears immediately.
- The collected-material list should be scrollable and visually align with the adjacent work panels.
- The user workflow should be obvious:
  1. Select one collected post.
  2. Select persona `小白`.
  3. Click generate in `二创草稿`.
  4. Edit title/body.
  5. Save draft.
  6. Suggest and add persona rules.

Avoid making the page a generic dashboard. It is a drafting workbench.

Persona management:

- Existing personas must be editable after selection.
- New persona creation should not accidentally overwrite the selected persona.
- Style changes that apply only to one persona should be added as persona rules.
- User edits are saved as draft final text first; `提炼规则` then turns AI-vs-user differences into candidate rules for that persona.

Image and export behavior:

- Original note images should be shown in both the original-material area and the remix/draft area.
- `复制 Markdown` copies text-oriented markdown only.
- `保存到本地` exports the draft markdown and copied images under `exports/`.
- Image display order has been user-corrected before. When changing image logic, inspect `backend/app/main.py` image ordering helpers and verify that the first Xiaohongshu image appears first in the workbench.

## Debugging Checklist

For `Failed to fetch`:

1. Confirm backend is running at `http://127.0.0.1:8000`.
2. Confirm frontend API base is `http://127.0.0.1:8000/api`.
3. Check backend terminal logs.
4. If logs show 400, surface the error in the UI.
5. If logs show 500, catch and translate the specific exception.

For empty collected posts:

```bash
sqlite3 data/app.db 'select id, keyword, title, author, likes, status from notes order by id desc limit 10;'
```

If `data/images` has files but `notes` is empty, inspect transaction behavior in `/api/collect`.

For collection that appears delayed or unchanged:

- OpenCLI collection can take time; the frontend should show a collecting/waiting hint.
- Duplicate Xiaohongshu links should not create duplicate note rows, so a repeated keyword may return fewer new materials.
- Check the `/api/collect` response, then inspect recent database rows:

  ```bash
  sqlite3 data/app.db 'select id, keyword, title, status, created_at from notes order by id desc limit 20;'
  ```

- If the backend collected records but the UI is stale, refresh notes after the collection promise finishes.

For generation not responding:

- Check `.env` exists at project root.
- Restart backend after `.env` edits.
- Use `MOCK_AI=true` to test the UI path.
- Use `python check_ai.py` to test MiniMax separately.

For port issues:

```bash
PORT=8010 python run.py
```

## Product Defaults

Default persona:

```text
小白：00后女大学生，语言生动活泼，喜欢用真实体验、轻松吐槽和口语化表达分享好吃好玩的东西。
```

Default initial rule:

```text
开头先给一个情绪钩子，让人马上知道这家店值不值得冲。
```

When improving the MVP, prefer small interaction upgrades that clarify the core workflow over broad feature expansion.
