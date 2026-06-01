import json
import os

from openai import APIError, AuthenticationError, OpenAI

from .config import get_settings


class AIServiceError(RuntimeError):
    pass


def _json_from_response_text(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _clean_api_key(value: str) -> str:
    key = str(value or "").strip().strip("'\"")
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    return key


class AIService:
    def __init__(self):
        self.settings = get_settings()

    def _client(self) -> OpenAI:
        if self.settings.ai_provider == "minimax":
            api_key = _clean_api_key(self.settings.minimax_api_key or os.getenv("MINIMAX_API_KEY", ""))
            if not api_key:
                raise AIServiceError("缺少 MINIMAX_API_KEY，请在 .env 或环境变量中配置后再生成。")
            return OpenAI(api_key=api_key, base_url=self.settings.minimax_base_url, timeout=self.settings.openai_timeout)

        api_key = _clean_api_key(self.settings.openai_api_key or os.getenv("OPENAI_API_KEY", ""))
        if not api_key:
            raise AIServiceError("缺少 OPENAI_API_KEY，请在 .env 或环境变量中配置后再生成。")
        return OpenAI(api_key=api_key, timeout=self.settings.openai_timeout)

    def _chat_json(self, system_prompt: str, payload: dict) -> dict:
        try:
            if self.settings.ai_provider == "minimax":
                response = self._client().chat.completions.create(
                    model=self.settings.minimax_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                    temperature=0.8,
                    max_completion_tokens=1800,
                )
                content = response.choices[0].message.content or ""
                return _json_from_response_text(content)

            response = self._client().responses.create(
                model=self.settings.openai_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
            return _json_from_response_text(response.output_text)
        except AuthenticationError as exc:
            provider = "MiniMax" if self.settings.ai_provider == "minimax" else "OpenAI"
            raise AIServiceError(f"{provider} API Key 无效或无权限，请检查 .env 中的 Key 是否复制完整。") from exc
        except APIError as exc:
            provider = "MiniMax" if self.settings.ai_provider == "minimax" else "OpenAI"
            raise AIServiceError(f"{provider} 接口调用失败：{exc}") from exc
        except json.JSONDecodeError as exc:
            raise AIServiceError("模型没有返回合法 JSON，请重试或换一个模型。") from exc

    def generate(self, note: dict, persona: dict, rules: list[str]) -> dict:
        if self.settings.mock_ai:
            return {
                "title": f"小白试吃笔记｜{note.get('title', '这家店有点东西')}",
                "body": (
                    f"家人们我先说结论：这条真的很适合用「{persona['name']}」的口吻重新种草。\n\n"
                    f"原帖重点是：{note.get('content', '')[:180]}\n\n"
                    "如果是我来写，会更像一个刚吃完立刻想发朋友圈的大学生：有真实感、有一点小激动，"
                    "但不硬夸，先把好吃点、适合谁去、要不要排队这些讲清楚。"
                ),
                "tags": ["北京美食", "小红书二创", persona["name"]],
                "image_advice": "优先使用第一张作为封面，后续图片按菜品细节到环境氛围排序。",
            }
        prompt = {
            "task": "把小红书原帖改写成指定人设风格的新帖。不要虚构没有依据的事实，不要保留原文长句。",
            "persona": {
                "name": persona["name"],
                "description": persona["description"],
                "rules": rules,
            },
            "source_note": {
                "title": note.get("title", ""),
                "author": note.get("author", ""),
                "content": note.get("content", ""),
                "likes": note.get("likes", 0),
            },
            "output_schema": {
                "title": "改写标题",
                "body": "改写正文",
                "tags": ["建议标签"],
                "image_advice": "图片使用建议",
            },
        }
        data = self._chat_json("你是小红书内容二创助手，只输出合法 JSON，不输出 Markdown。", prompt)
        required = {"title", "body", "tags", "image_advice"}
        if not required.issubset(data):
            raise AIServiceError("OpenAI 返回字段不完整，请重试。")
        if not isinstance(data["tags"], list):
            data["tags"] = [str(data["tags"])]
        return data

    def suggest_rules(self, persona: dict, before_title: str, before_body: str, after_title: str, after_body: str) -> list[str]:
        if self.settings.mock_ai:
            return [
                "标题要更像朋友安利，减少总结感。",
                "正文开头先给结论，再补体验细节。",
                "多用短句和口语化连接词，降低官方感。",
            ]
        prompt = {
            "task": "对比 AI 初稿和用户终稿，总结可复用的人设写作规则。只给规则，不要评价。",
            "persona": persona,
            "before": {"title": before_title, "body": before_body},
            "after": {"title": after_title, "body": after_body},
            "output_schema": {"rules": ["规则1", "规则2"]},
        }
        data = self._chat_json("你是风格规则提炼助手，只输出合法 JSON。", prompt)
        rules = data.get("rules", [])
        if not isinstance(rules, list):
            raise AIServiceError("OpenAI 返回规则格式不正确，请重试。")
        return [str(rule).strip() for rule in rules if str(rule).strip()]
