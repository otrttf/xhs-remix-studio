from pathlib import Path
import difflib
import re
import shutil
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .ai_service import AIService, AIServiceError
from .config import get_settings
from .database import get_db, init_db, now_iso, row_to_dict
from .opencli_client import OpenCLIClient, OpenCLIError


app = FastAPI(title="Xiaohongshu Remix Studio")
settings = get_settings()
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=settings.database_path.parent.parent), name="assets")


class CollectRequest(BaseModel):
    keyword: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


class PersonaRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class RuleRequest(BaseModel):
    rule_text: str = Field(min_length=1)


class GenerateRequest(BaseModel):
    note_id: int
    persona_id: int


class SaveDraftRequest(BaseModel):
    final_title: str = Field(min_length=1)
    final_body: str = Field(min_length=1)


def _note_with_images(conn, note_id: int) -> dict:
    note = row_to_dict(conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone())
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    images = [dict(row) for row in conn.execute("SELECT * FROM note_images WHERE note_id = ? ORDER BY sort_order", (note_id,))]
    images = _display_ordered_images(images)
    note["images"] = images
    return note


def _display_ordered_images(images: list[dict]) -> list[dict]:
    ordered = sorted(images, key=_image_order_key)
    if len(ordered) > 1:
        return [*ordered[1:], ordered[0]]
    return ordered


def _image_order_key(image: dict) -> tuple:
    name = Path(image.get("local_path", "")).stem
    numbers = re.findall(r"\d+", name)
    numeric = int(numbers[-1]) if numbers else int(image.get("sort_order") or 0)
    return (numeric, image.get("local_path", ""))


def _safe_filename(value: str, fallback: str = "draft") -> str:
    name = re.sub(r"[\\/:*?\"<>|\s]+", "-", value).strip("-")
    return name[:80] or fallback


def _draft_markdown(draft: dict, note: dict, image_prefix: str = "") -> str:
    title = draft["final_title"] or draft["generated_title"]
    body = draft["final_body"] or draft["generated_body"]
    image_lines = []
    for image in note["images"]:
        path = Path(image["local_path"]).name if image_prefix else image["local_path"]
        image_lines.append(f"![图片]({image_prefix}{path})")
    images = "\n".join(image_lines)
    return f"# {title}\n\n{body}\n\n## 建议标签\n{draft['suggested_tags']}\n\n## 图片\n{images}\n"


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "opencli": OpenCLIClient().check_available(),
        "ai_provider": settings.ai_provider,
        "model": settings.minimax_model if settings.ai_provider == "minimax" else settings.openai_model,
        "mock_ai": settings.mock_ai,
    }


@app.post("/api/collect")
def collect_notes(payload: CollectRequest):
    client = OpenCLIClient()
    try:
        candidates = client.search(payload.keyword, payload.limit)
    except OpenCLIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stats = {"found": len(candidates), "saved": 0, "failed": 0}
    saved_notes = []
    with get_db() as conn:
        for candidate in candidates:
            now = now_iso()
            try:
                detail = client.note_detail(candidate["url"])
                candidate.update(detail)
                candidate["status"] = "ok"
                candidate["error_message"] = ""
            except OpenCLIError as exc:
                candidate["status"] = "failed"
                candidate["error_message"] = str(exc)
                stats["failed"] += 1

            conn.execute(
                """
                INSERT INTO notes
                (note_key, keyword, title, author, content, likes, collects, comments, url, status, error_message, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(note_key) DO UPDATE SET
                    keyword = excluded.keyword,
                    title = excluded.title,
                    author = excluded.author,
                    content = excluded.content,
                    likes = excluded.likes,
                    collects = excluded.collects,
                    comments = excluded.comments,
                    url = excluded.url,
                    status = excluded.status,
                    error_message = excluded.error_message,
                    collected_at = excluded.collected_at
                """,
                (
                    candidate["note_key"],
                    payload.keyword,
                    candidate.get("title", ""),
                    candidate.get("author", ""),
                    candidate.get("content", ""),
                    candidate.get("likes", 0),
                    candidate.get("collects", 0),
                    candidate.get("comments", 0),
                    candidate["url"],
                    candidate["status"],
                    candidate["error_message"],
                    now,
                ),
            )
            note_id = conn.execute("SELECT id FROM notes WHERE note_key = ?", (candidate["note_key"],)).fetchone()["id"]
            if candidate["status"] == "ok":
                try:
                    images = client.download_images(candidate["url"], candidate["note_key"])
                    for image in images:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO note_images (note_id, local_path, sort_order, file_size)
                            VALUES (?, ?, ?, ?)
                            """,
                            (note_id, image["local_path"], image["sort_order"], image["file_size"]),
                        )
                except OpenCLIError as exc:
                    conn.execute("UPDATE notes SET status = ?, error_message = ? WHERE id = ?", ("partial", str(exc), note_id))
            stats["saved"] += 1
            saved_notes.append(_note_with_images(conn, note_id))
    return {"stats": stats, "notes": saved_notes}


@app.get("/api/notes")
def list_notes(keyword: Optional[str] = None):
    with get_db() as conn:
        params = []
        query = "SELECT * FROM notes"
        if keyword:
            query += " WHERE keyword LIKE ?"
            params.append(f"%{keyword}%")
        query += " ORDER BY collected_at DESC, id DESC"
        rows = [dict(row) for row in conn.execute(query, params)]
        for note in rows:
            note["images"] = [
                dict(row)
                for row in conn.execute("SELECT * FROM note_images WHERE note_id = ? ORDER BY sort_order", (note["id"],))
            ]
            note["images"] = _display_ordered_images(note["images"])
        return rows


@app.get("/api/notes/{note_id}")
def get_note(note_id: int):
    with get_db() as conn:
        return _note_with_images(conn, note_id)


@app.get("/api/personas")
def list_personas():
    with get_db() as conn:
        personas = [dict(row) for row in conn.execute("SELECT * FROM personas ORDER BY id")]
        for persona in personas:
            persona["rules"] = [
                dict(row)
                for row in conn.execute("SELECT * FROM persona_rules WHERE persona_id = ? ORDER BY id", (persona["id"],))
            ]
        return personas


@app.post("/api/personas")
def create_persona(payload: PersonaRequest):
    now = now_iso()
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO personas (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (payload.name, payload.description, now, now),
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail="人设名称已存在或数据不合法") from exc
        return row_to_dict(conn.execute("SELECT * FROM personas WHERE id = ?", (cursor.lastrowid,)).fetchone())


@app.put("/api/personas/{persona_id}")
def update_persona(persona_id: int, payload: PersonaRequest):
    with get_db() as conn:
        conn.execute(
            "UPDATE personas SET name = ?, description = ?, updated_at = ? WHERE id = ?",
            (payload.name, payload.description, now_iso(), persona_id),
        )
        persona = row_to_dict(conn.execute("SELECT * FROM personas WHERE id = ?", (persona_id,)).fetchone())
        if not persona:
            raise HTTPException(status_code=404, detail="人设不存在")
        return persona


@app.post("/api/personas/{persona_id}/rules")
def add_rule(persona_id: int, payload: RuleRequest):
    with get_db() as conn:
        if not conn.execute("SELECT id FROM personas WHERE id = ?", (persona_id,)).fetchone():
            raise HTTPException(status_code=404, detail="人设不存在")
        cursor = conn.execute(
            "INSERT INTO persona_rules (persona_id, rule_text, created_at) VALUES (?, ?, ?)",
            (persona_id, payload.rule_text, now_iso()),
        )
        return row_to_dict(conn.execute("SELECT * FROM persona_rules WHERE id = ?", (cursor.lastrowid,)).fetchone())


@app.delete("/api/persona-rules/{rule_id}")
def delete_rule(rule_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM persona_rules WHERE id = ?", (rule_id,))
        return {"ok": True}


@app.post("/api/drafts/generate")
def generate_draft(payload: GenerateRequest):
    with get_db() as conn:
        note = _note_with_images(conn, payload.note_id)
        persona = row_to_dict(conn.execute("SELECT * FROM personas WHERE id = ?", (payload.persona_id,)).fetchone())
        if not persona:
            raise HTTPException(status_code=404, detail="人设不存在")
        rules = [row["rule_text"] for row in conn.execute("SELECT rule_text FROM persona_rules WHERE persona_id = ?", (payload.persona_id,))]
        try:
            generated = AIService().generate(note, persona, rules)
        except AIServiceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        now = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO drafts
            (note_id, persona_id, generated_title, generated_body, suggested_tags, image_advice, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'generated', ?, ?)
            """,
            (
                payload.note_id,
                payload.persona_id,
                generated["title"],
                generated["body"],
                ",".join(generated["tags"]),
                generated["image_advice"],
                now,
                now,
            ),
        )
        return row_to_dict(conn.execute("SELECT * FROM drafts WHERE id = ?", (cursor.lastrowid,)).fetchone())


@app.get("/api/drafts")
def list_drafts():
    with get_db() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM drafts ORDER BY updated_at DESC")]


@app.put("/api/drafts/{draft_id}")
def save_draft(draft_id: int, payload: SaveDraftRequest):
    with get_db() as conn:
        draft = row_to_dict(conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone())
        if not draft:
            raise HTTPException(status_code=404, detail="草稿不存在")
        before = f"{draft['generated_title']}\n{draft['generated_body']}".splitlines()
        after = f"{payload.final_title}\n{payload.final_body}".splitlines()
        diff_summary = "\n".join(difflib.unified_diff(before, after, lineterm=""))[:4000]
        conn.execute(
            """
            UPDATE drafts SET final_title = ?, final_body = ?, status = 'saved', updated_at = ? WHERE id = ?
            """,
            (payload.final_title, payload.final_body, now_iso(), draft_id),
        )
        conn.execute(
            """
            INSERT INTO edit_events
            (draft_id, persona_id, before_title, before_body, after_title, after_body, diff_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                draft["persona_id"],
                draft["generated_title"],
                draft["generated_body"],
                payload.final_title,
                payload.final_body,
                diff_summary,
                now_iso(),
            ),
        )
        return row_to_dict(conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone())


@app.post("/api/drafts/{draft_id}/suggest-rules")
def suggest_rules(draft_id: int):
    with get_db() as conn:
        draft = row_to_dict(conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone())
        if not draft or not draft.get("final_body"):
            raise HTTPException(status_code=400, detail="请先保存编辑后的终稿")
        persona = row_to_dict(conn.execute("SELECT * FROM personas WHERE id = ?", (draft["persona_id"],)).fetchone())
        try:
            rules = AIService().suggest_rules(
                persona,
                draft["generated_title"],
                draft["generated_body"],
                draft["final_title"],
                draft["final_body"],
            )
        except AIServiceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"rules": rules}


@app.get("/api/export/drafts/{draft_id}.md")
def export_draft(draft_id: int):
    with get_db() as conn:
        draft = row_to_dict(conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone())
        if not draft:
            raise HTTPException(status_code=404, detail="草稿不存在")
        note = _note_with_images(conn, draft["note_id"])
        return {"markdown": _draft_markdown(draft, note, image_prefix="/assets/")}


@app.post("/api/export/drafts/{draft_id}/local")
def export_draft_local(draft_id: int):
    with get_db() as conn:
        draft = row_to_dict(conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone())
        if not draft:
            raise HTTPException(status_code=404, detail="草稿不存在")
        note = _note_with_images(conn, draft["note_id"])

    title = draft["final_title"] or draft["generated_title"]
    export_root = settings.database_path.parent.parent / "exports"
    export_dir = export_root / f"draft-{draft_id}-{_safe_filename(title)}"
    export_dir.mkdir(parents=True, exist_ok=True)

    copied_images = []
    for image in note["images"]:
        source = settings.database_path.parent.parent / image["local_path"]
        if not source.exists():
            continue
        target = export_dir / source.name
        shutil.copy2(source, target)
        copied_images.append(str(target))

    markdown = _draft_markdown(draft, note, image_prefix="./")
    markdown_path = export_dir / "draft.md"
    markdown_path.write_text(markdown, encoding="utf-8")

    return {
        "ok": True,
        "export_dir": str(export_dir),
        "markdown_path": str(markdown_path),
        "image_count": len(copied_images),
    }
