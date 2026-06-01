from dotenv import load_dotenv
from openai import OpenAI
import os
import sys


load_dotenv("../.env")


def clean_key(value: str) -> str:
    key = str(value or "").strip().strip("'\"")
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    return key


def main() -> int:
    provider = os.getenv("AI_PROVIDER", "openai").lower()
    if provider != "minimax":
        print("This checker currently targets AI_PROVIDER=minimax.")
        return 1

    key = clean_key(os.getenv("MINIMAX_API_KEY", ""))
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
    model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
    if not key:
        print("MINIMAX_API_KEY is empty.")
        return 1

    client = OpenAI(api_key=key, base_url=base_url, timeout=30)
    print(f"Testing MiniMax endpoint: {base_url}")
    print(f"Testing model: {model}")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "只回复 JSON：{\"ok\":true}"}],
        max_completion_tokens=64,
    )
    print(response.choices[0].message.content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
