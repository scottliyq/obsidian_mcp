import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

import structlog
from fastmcp import Context, FastMCP

from app.bootstrap import Services, build_services
from app.core.config import AppConfig, load_config
from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)


@dataclass
class AppContext:
    config: AppConfig
    services: Services
    watcher_task: asyncio.Task[None] | None


def create_server(config_path: Path) -> FastMCP:
    @asynccontextmanager
    async def lifespan(_: FastMCP):
        config = load_config(config_path)
        configure_logging(config.server.log_level)
        services = build_services(config)
        await services.indexer.index_all(force=False)
        watcher_task = asyncio.create_task(services.watcher.run())
        logger.info("mcp_started", vaults=len(config.vaults))
        try:
            yield AppContext(config=config, services=services, watcher_task=watcher_task)
        finally:
            if watcher_task:
                watcher_task.cancel()
                with suppress(asyncio.CancelledError):
                    await watcher_task
            await services.embedding.close()
            logger.info("mcp_stopped")

    mcp = FastMCP("obsidian-mcp", lifespan=lifespan)

    @mcp.tool()
    async def search(
        query: str,
        vault: str | None = None,
        top_k: int = 5,
        ctx: Context | None = None,
    ) -> dict:
        """在 Obsidian 向量库中执行语义检索。

        Args:
            query: 必填，检索查询文本。
            vault: 可选，限定检索的 vault 名称；为空时检索全部 vault。
            top_k: 可选，返回结果数量上限，默认 5。

        Returns:
            包含 `results` 列表的字典。每个结果包含 `vault`、`path`、`score`、`snippet`、`chunk_id`。
        """
        if ctx is None:
            raise ValueError("MCP context is required")
        app_ctx: AppContext = ctx.lifespan_context
        results = await app_ctx.services.search.search(query=query, vault_name=vault, top_k=top_k)
        payload = [
            {
                "vault": result.vault,
                "path": result.path,
                "score": result.score,
                "snippet": result.snippet,
                "chunk_id": result.chunk_id,
            }
            for result in results
        ]
        return {"results": payload}

    return mcp
