# AI 客服信件分類器（Python + Ollama + GitHub Pages）

本專題使用 Python 呼叫本機 Ollama，將客服信件整理成案件分類、優先級、問題摘要與建議回覆。模型輸出採用 JSON Schema 結構化輸出，程式會驗證欄位與允許值。

## 環境需求
- Python 3.10+
- uv
- Ollama

## 安裝與執行
先安裝並啟動 Ollama，再執行：

```bash
ollama pull qwen2.5:3b
uv sync
uv run python -m faq_assistant.main --ticket "我已付款成功，但系統仍顯示未付款，無法使用服務。"
```

預設輸出為 `docs/index.html`。若要產生靜態示範頁（不呼叫模型）：

```bash
uv run python -m faq_assistant.main --demo --output docs/index.html
```

## AI 技術
- Python `urllib.request` 呼叫 Ollama `/api/chat`。
- 將 JSON Schema 傳入 `format` 欄位，限制輸出欄位及允許值。
- 程式檢查四個欄位是否存在、是否為非空字串，並驗證分類與優先級。
- 預設模型 `qwen2.5:3b`，可用 `OLLAMA_HOST`、`OLLAMA_MODEL` 環境變數修改（範例見 `.env.example`）。

## GitHub Pages 部署
1. Repository Settings → Pages。
2. Build and deployment 的 Source 選擇 GitHub Actions。
3. 推送到 `main` 後，Actions 會自動產生展示頁並部署。

注意：Actions 使用 `--demo` 產生靜態展示頁，不會在 GitHub runner 呼叫 Ollama。即時 AI 分析需在已安裝 Ollama 的本機執行。不要提交 `.env`、Token、密碼或私人客服資料。

## 專案結構
```text
.github/workflows/deploy.yml
faq_assistant/__init__.py
faq_assistant/main.py
docs/index.html
.env.example
.gitignore
pyproject.toml
README.md
```
