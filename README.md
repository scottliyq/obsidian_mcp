# obsidian_mcp

本项目提供 Obsidian Vault 的 MCP 向量检索服务，支持多 vault、文件变更监听、向量持久化与 MCP `search` 工具检索。嵌入模型使用本地 Ollama（如 `nomic-embed-text` / `qllama/bge-small-zh-v1.5`）。

## 功能
- 支持多个 Obsidian vault
- 监听 `.md` 文件新增/修改/删除
- 向量化并持久化（Chroma）
- MCP `search` 工具提供检索能力
- CLI 强制全量索引
- 启动时增量索引（基于 mtime/sha1）

## 依赖
- Python 3.12
- fastmcp
- chromadb
- httpx
- watchfiles
- pyyaml
- structlog
- pytest
- pytest-asyncio

## 快速开始
1) 配置 `config.yaml`（示例已提供）
2) 启动 MCP 服务（stdio）：

```bash
python -m app.main
```

3) 强制索引：

```bash
python -m app.cli index --all
python -m app.cli index --vault <vault_name>
```

## 测试
```bash
pytest -q
```

## 常见问题
- 如果启动时报 `Ollama embedding endpoint not found`，请检查：
  - `config.yaml` 的 `embedding.ollama_base_url`
  - Ollama 服务是否在运行
  - embedding 模型是否已拉取（如 `ollama pull nomic-embed-text` 或 `ollama pull qllama/bge-small-zh-v1.5`）
- 如果报 `the input length exceeds the context length`，说明单个分块过长，会自动降级切分；如仍失败请降低 `chunk_size_chars`。

## MCP Tool
- `search(query: str, vault: str | None = None, top_k: int = 5)`

返回：
- `results: list[{vault, path, score, snippet, chunk_id}]`

## MCP 配置示例（VS Code Copilot）
在项目下新建 `/Users/scottliyq/go/ai/obsidian_mcp/.vscode/mcp.json`：

```json
{
  "servers": {
    "obsidian-mcp": {
      "command": "python",
      "args": ["-m", "app.main"],
      "cwd": "/Users/scottliyq/go/ai/obsidian_mcp"
    }
  }
}
```

## 配置
`config.yaml` 关键字段：
- `vaults[].chunking` 可按 vault 覆盖分块策略与大小
- `vaults[].embedding_model` 可按 vault 指定 embedding 模型

## 修改记录
- 2026-02-20：实现多 vault MCP 服务、Chroma 向量持久化、Ollama 嵌入、文件监听与 CLI 索引，满足按 vault 配置与强制全量索引需求。
- 2026-02-20：新增 `requirements.txt` 与基础测试（chunking/indexer/cli），补充测试说明；移除外部分块依赖，改为内置递归分块器。
- 2026-02-20：移除 FastMCP 过期参数 `json_response` 以兼容当前版本。
- 2026-02-20：httpx 启用 socks 额外依赖，修复 SOCKS 代理缺少 `socksio` 的启动错误。
- 2026-02-20：Ollama 404 时输出更明确的错误提示与排查建议。
- 2026-02-20：修正中文默认 embedding 模型为 `qllama/bge-small-zh-v1.5`。
- 2026-02-20：Ollama 400 时记录响应体，过滤空文本避免无效请求。
- 2026-02-20：遇到上下文长度超限时自动降级切分并重试。
- 2026-02-20：启动时基于 mtime/sha1 做增量索引，记录索引状态。
- 2026-02-20：修复 Chroma query include 参数不接受 ids 的问题。
- 2026-02-21：新增 `.vscode/mcp.json` 的 `obsidian-mcp` 服务配置（`python -m app.main`），并在 `py312obsync` 环境下完成服务启动与进程确认，便于在编辑器内直接调用 MCP 服务。
- 2026-02-21：下调 `config.yaml` 分块参数（`default_chunk_size_chars/chunk_size_chars: 800 -> 600`，`default_chunk_overlap_chars/chunk_overlap_chars: 120 -> 80`），降低 Ollama `context length` 超限概率。
- 2026-02-21：将 `.vscode/mcp.json` 的 `obsidian-mcp.command` 改为 `py312obsync` 环境 Python 绝对路径，确保 MCP 始终在指定 conda 环境下启动。
- 2026-02-21：为 MCP `search` 工具补充描述文档（docstring），修复客户端告警 `Tool search does not have a description`。
