"""
Tool registry — single source of truth for every tool available to the agent.

ToolRegistry is instantiated once per agent instance. It:
  - Constructs each tool with the credentials it needs
  - Wraps each tool's execute function into a uniform async callable
  - Exposes get_tool_definitions() and execute_tool() to the agent loop
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine

from app.config import Settings

logger = logging.getLogger(__name__)

# Per-tool call timeout (seconds)
TOOL_TIMEOUT = 30.0


class ToolRegistry:

    def __init__(self, config: Settings) -> None:
        """
        Instantiate all tools and build the executor map.

        Each entry in self._executors is a coroutine function with the
        uniform signature:  async (tool_name: str, tool_input: dict) -> str
        """
        # Lazy imports keep startup fast and avoid circular imports
        from app.tools.scorecard import (
            execute as _scorecard_execute,
            get_tool_definitions as _scorecard_defs,
        )
        from app.tools.page_fetcher import (
            execute as _page_fetcher_execute,
            get_tool_definition as _page_fetcher_def,
        )
        from app.tools.web_search import (
            execute as _web_search_execute,
            get_tool_definition as _web_search_def,
        )
        from app.tools.cost_of_living import (
            execute as _col_execute,
            get_tool_definition as _col_def,
        )
        from app.tools.reddit_search import (
            execute as _reddit_execute,
            get_tool_definition as _reddit_def,
        )

        self._config = config

        # --- Capture credentials once so closures don't call require_* on every call ---
        scorecard_key = config.SCORECARD_API_KEY or ""

        # Uniform wrappers: (tool_name, tool_input) -> str
        async def _scorecard(tool_name: str, tool_input: dict) -> str:
            return await _scorecard_execute(
                tool_name=tool_name,
                tool_input=tool_input,
                api_key=scorecard_key,
            )

        async def _page_fetcher(tool_name: str, tool_input: dict) -> str:
            return await _page_fetcher_execute(
                tool_name=tool_name,
                tool_input=tool_input,
                config=config,
            )

        async def _web_search(tool_name: str, tool_input: dict) -> str:
            return await _web_search_execute(
                tool_name=tool_name,
                tool_input=tool_input,
            )

        async def _col(tool_name: str, tool_input: dict) -> str:
            return await _col_execute(
                tool_name=tool_name,
                tool_input=tool_input,
            )

        async def _reddit(tool_name: str, tool_input: dict) -> str:
            return await _reddit_execute(
                tool_name=tool_name,
                tool_input=tool_input,
            )

        # Map every Claude tool name → its executor
        self._executors: dict[str, Callable[..., Coroutine[Any, Any, str]]] = {
            "search_us_universities": _scorecard,
            "get_university_details": _scorecard,
            "fetch_university_page": _page_fetcher,
            "web_search": _web_search,
            "get_living_costs": _col,
            "search_student_discussions": _reddit,
        }

        # Collect tool definitions once at startup
        self._tool_definitions: list[dict[str, Any]] = [
            *_scorecard_defs(),
            _page_fetcher_def(),
            _web_search_def(),
            _col_def(),
            _reddit_def(),
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return all tool definitions in the format Claude expects."""
        return self._tool_definitions

    async def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """
        Execute a tool by name with a per-call timeout.

        Returns a JSON string in all cases — errors are returned as
        {"error": "..."} so the agent loop can pass them back to Claude
        rather than crashing.
        """
        executor = self._executors.get(tool_name)
        if executor is None:
            logger.warning("Unknown tool requested: %s", tool_name)
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                executor(tool_name, tool_input),
                timeout=TOOL_TIMEOUT,
            )
            elapsed = time.monotonic() - start
            logger.info("Tool %s completed in %.2fs", tool_name, elapsed)
            return result

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            logger.error("Tool %s timed out after %.1fs", tool_name, elapsed)
            return json.dumps({
                "error": f"Tool '{tool_name}' timed out after {TOOL_TIMEOUT:.0f}s. "
                         "Try a more specific query or check the source directly.",
            })

        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.exception("Tool %s failed after %.2fs: %s", tool_name, elapsed, exc)
            return json.dumps({
                "error": f"Tool '{tool_name}' encountered an error: {exc}",
            })


# ---------------------------------------------------------------------------
# Module-level helpers kept for backward compatibility
# (used by tests and any code that hasn't migrated to the class yet)
# ---------------------------------------------------------------------------

from app.config import settings as _settings  # noqa: E402

_registry: ToolRegistry | None = None


def _get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry(_settings)
    return _registry


# Lazy property — evaluated on first access so tests can patch settings first
def __getattr__(name: str) -> Any:
    if name == "TOOL_DEFINITIONS":
        return _get_registry().get_tool_definitions()
    raise AttributeError(name)


async def dispatch_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Module-level shim for backward compatibility."""
    return await _get_registry().execute_tool(tool_name, tool_input)
