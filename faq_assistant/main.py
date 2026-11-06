from __future__ import annotations

import argparse
import html
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": ["帳務付款", "技術問題", "帳號使用", "其他"]},
        "priority": {"type": "string", "enum": ["高", "中", "低"]},
        "summary": {"type": "string"},
        "suggested_reply": {"type": "string"}
    },
    "required": ["category", "priority", "summary", "suggested_reply"]
}

SYSTEM_PROMPT = """你是專業的繁體中文客服案件分類助理。
請根據使用者提供的客服信件，判斷分類與優先級，並產生簡潔、有禮貌且可執行的回覆。
分類只能是：帳務付款、技術問題、帳號使用、其他。
優先級只能是：高、中、低。
若涉及帳號安全、付款失敗造成服務中斷或大量用戶受影響，優先級應提高。
只輸出符合指定 JSON schema 的內容，不要輸出 Markdown。"""

DEMO_TICKET = (
    "你好，我昨天已經付款成功，信用卡也收到扣款通知，"
    "但登入後系統仍顯示尚未付款，無法使用進階功能。"
    "請幫我確認，謝謝。"
)

DEMO_RESULT = {
    "category": "帳務付款",
    "priority": "高",
    "summary": "使用者已完成信用卡付款，但系統仍顯示未付款，導致無法使用進階功能。",
    "suggested_reply": "您好，造成您的困擾非常抱歉。我們會先核對交易紀錄與帳務狀態，請您提供訂單編號或付款時間（請勿提供完整信用卡號）。確認後會協助更新付款狀態，謝謝您的耐心等候。"
}


def call_ollama(ticket: str) -> dict:
    """Call Ollama chat API and request schema-constrained structured JSON output."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    payload = {
        "model": model,
        "stream": False,
        "format": SCHEMA,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"請分析以下客服信件：\n{ticket}"}
        ],
        "options": {"temperature": 0.2}
    }
    request = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
        result = json.loads(data["message"]["content"])
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"無法連線 Ollama（{host}）。請確認 Ollama 已啟動，並已執行 "
            f"`ollama pull {model}`。詳細資訊：{exc}"
        ) from exc
    except (KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama 回傳格式不正確：{exc}") from exc

    for key in ("category", "priority", "summary", "suggested_reply"):
        if not isinstance(result.get(key), str) or not result[key].strip():
            raise RuntimeError(f"模型輸出缺少有效欄位：{key}")
    if result["category"] not in SCHEMA["properties"]["category"]["enum"]:
        raise RuntimeError("模型輸出的 category 不在允許範圍內")
    if result["priority"] not in SCHEMA["properties"]["priority"]["enum"]:
        raise RuntimeError("模型輸出的 priority 不在允許範圍內")
    return result


def render_page(ticket: str, result: dict, mode: str, output: Path) -> None:
    esc = lambda value: html.escape(str(value))
    priority_class = {"高": "high", "中": "medium", "低": "low"}.get(result["priority"], "")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 客服信件分類器</title>
<style>
:root{{--ink:#202938;--muted:#64748b;--line:#e5eaf1;--brand:#4f46e5;--bg:#f5f7fb}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Noto Sans TC",sans-serif;line-height:1.7}}
header{{background:linear-gradient(120deg,#312e81,#6366f1);color:white;padding:48px 22px}}
.wrap{{max-width:920px;margin:auto}}h1{{font-size:clamp(28px,5vw,42px);margin:0 0 8px}}header p{{margin:0;color:#e0e7ff}}
main{{max-width:920px;margin:28px auto;padding:0 18px}}section{{background:white;border:1px solid var(--line);border-radius:16px;padding:24px;margin:18px 0;box-shadow:0 5px 20px #1725540a}}
h2{{font-size:20px;margin:0 0 14px}}.muted{{color:var(--muted);font-size:14px}}.ticket,.reply{{white-space:pre-wrap;background:#f8fafc;border:1px solid var(--line);border-radius:10px;padding:16px}}
.pills{{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 16px}}.pill{{padding:5px 12px;border-radius:999px;background:#eef2ff;color:#3730a3;font-weight:700;font-size:14px}}
.high{{background:#fee2e2;color:#991b1b}}.medium{{background:#fef3c7;color:#92400e}}.low{{background:#dcfce7;color:#166534}}
.steps{{padding-left:22px}}footer{{text-align:center;color:var(--muted);padding:28px;font-size:13px}}
code{{background:#eef2ff;padding:2px 6px;border-radius:5px}}
</style>
</head>
<body>
<header><div class="wrap"><h1>AI 客服信件分類器</h1><p>使用 Python + Ollama，將客服信件轉成結構化案件資訊與建議回覆。</p></div></header>
<main>
<section><h2>1. 做了什麼</h2><p>輸入一段客服信件，AI 會自動判斷案件分類、優先級、問題摘要，並產生客服建議回覆，協助客服人員快速整理案件。</p><p class="muted">技術：Python 3.10+、uv、Ollama、qwen2.5:3b、JSON Schema 結構化輸出。</p></section>
<section><h2>2. 執行方式</h2><ol class="steps"><li>安裝 Python 與 uv。</li><li>安裝並啟動 Ollama。</li><li>執行 <code>ollama pull qwen2.5:3b</code>。</li><li>在專案目錄執行 <code>uv run python -m faq_assistant.main --ticket "你的客服信件"</code>。</li><li>程式呼叫 Ollama API，將結果輸出成 <code>docs/index.html</code>。</li></ol></section>
<section><h2>3. 執行結果</h2><p class="muted">目前展示：{esc(mode)} · 產生時間：{esc(generated)}</p><h3>輸入的客服信件</h3><div class="ticket">{esc(ticket)}</div><div class="pills"><span class="pill">分類：{esc(result["category"])}</span><span class="pill {priority_class}">優先級：{esc(result["priority"])}</span></div><h3>問題摘要</h3><p>{esc(result["summary"])}</p><h3>AI 建議回覆</h3><div class="reply">{esc(result["suggested_reply"])}</div></section>
<section><h2>4. AI 使用說明</h2><ul><li><b>模型：</b>Ollama 本機模型 qwen2.5:3b。</li><li><b>呼叫方式：</b>Python 使用標準函式庫 urllib 呼叫 Ollama 的 <code>/api/chat</code>。</li><li><b>AI 能力：</b>使用 JSON Schema 限制輸出欄位與允許值，屬於結構化輸出（Structured Output）。</li><li><b>自行修改與驗證：</b>可修改 <code>SYSTEM_PROMPT</code>、分類選項與優先級規則；程式會再次檢查模型回傳欄位及 enum 值。</li><li><b>資料安全：</b>預設使用本機 Ollama，不需將客服信件送到第三方雲端 API；仍應避免輸入密碼、完整信用卡號等敏感資料。</li></ul></section>
<section><h2>專案原始碼</h2><p>完整程式與自動部署設定請見 GitHub Repository。GitHub Actions 會以示範資料產生此頁面並部署到 GitHub Pages。</p><p class="muted">此頁面是靜態展示頁；實際 AI 分析需在已安裝並啟動 Ollama 的電腦執行 Python 程式。</p></section>
</main><footer>AI 客服信件分類器 · Python / Ollama / GitHub Actions / GitHub Pages</footer>
</body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="AI 客服信件分類器（Ollama）")
    parser.add_argument("--ticket", help="要分析的客服信件內容")
    parser.add_argument("--demo", action="store_true", help="使用固定示範資料產生 Pages，不呼叫模型")
    parser.add_argument("--output", default="docs/index.html", help="HTML 輸出路徑")
    args = parser.parse_args()

    if args.demo:
        ticket, result, mode = DEMO_TICKET, DEMO_RESULT, "GitHub Actions 示範資料（非即時模型呼叫）"
    else:
        if not args.ticket:
            parser.error("請提供 --ticket，或使用 --demo")
        ticket = args.ticket
        try:
            result = call_ollama(ticket)
        except RuntimeError as exc:
            print(f"錯誤：{exc}", file=sys.stderr)
            return 1
        mode = "Ollama 本機模型即時分析"

    output = Path(args.output)
    render_page(ticket, result, mode, output)
    print(json.dumps({"ticket": ticket, **result, "html": str(output)}, ensure_ascii=False, indent=2))
    print(f"\n網頁已產生：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
