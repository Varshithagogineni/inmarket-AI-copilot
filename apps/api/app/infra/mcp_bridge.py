"""Bridge between the API backend and the MCP Server.

Provides MCPBridge — a client that connects to the FastMCP server
via stdio transport and invokes MCP tools. This is used by the
LangChain agent so tool calls go THROUGH the MCP protocol,
demonstrating true MCP integration.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Path to the MCP server module
_MCP_SERVER_DIR = str(Path(__file__).resolve().parents[3] / "mcp")


class MCPBridge:
    """Synchronous wrapper around the FastMCP client.

    Spawns the MCP server as a subprocess and communicates via stdio
    using the MCP protocol. Falls back to direct function imports
    if the MCP server cannot be started.
    """

    def __init__(self):
        self._client = None
        self._fallback = False
        self._tools_module = {}

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool by name with the given arguments.

        Tries the MCP client first; falls back to direct import if unavailable.
        """
        # Try MCP protocol via fastmcp Client
        try:
            return self._call_via_mcp(tool_name, arguments)
        except Exception:
            pass

        # Fallback: direct import of MCP tool functions
        return self._call_direct(tool_name, arguments)

    def _call_via_mcp(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via MCP protocol using fastmcp Client.

        Connects to the FastMCP server using stdio transport — the server
        is spawned as a subprocess and communication uses the MCP protocol.
        """
        try:
            from fastmcp import Client
        except ImportError:
            raise RuntimeError("fastmcp not installed")

        async def _run():
            # Use python -m to run the MCP server module properly
            import subprocess
            python_exe = sys.executable
            server_cmd = [python_exe, "-m", "app.server"]
            async with Client(server_cmd, cwd=_MCP_SERVER_DIR) as client:
                result = await client.call_tool(tool_name, arguments)
                # result is a list of content objects
                if result and hasattr(result[0], 'text'):
                    return json.loads(result[0].text)
                return {"status": "ok", "payload": str(result)}

        # Run async code synchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context, create new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _run())
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(_run())
        except RuntimeError:
            return asyncio.run(_run())

    def _call_direct(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: import MCP tool functions directly and call them.

        Adds the MCP server directory to sys.path so its tool modules
        can be imported. This provides the same functionality as the MCP
        protocol path but without the subprocess overhead.
        """
        # Add MCP server to path if needed
        if _MCP_SERVER_DIR not in sys.path:
            sys.path.insert(0, _MCP_SERVER_DIR)

        tool_map = self._get_tool_map()
        fn = tool_map.get(tool_name)
        if fn is None:
            return {"status": "error", "payload": {"message": "Unknown MCP tool: {0}".format(tool_name)}}

        try:
            result = fn(**arguments)
            return result if isinstance(result, dict) else {"status": "ok", "payload": result}
        except Exception as exc:
            return {"status": "error", "payload": {"message": str(exc)}}

    def _get_tool_map(self):
        """Lazy-load MCP tool function references."""
        if self._tools_module:
            return self._tools_module

        try:
            from app.tools.events import search_events, get_event_details
            from app.tools.strategy import score_event_fit, rank_event_candidates
            from app.tools.creative import (
                generate_campaign_brief,
                generate_copy_variants,
                generate_image_prompt,
                generate_draft_poster,
            )
            self._tools_module = {
                "search_events": search_events,
                "get_event_details": get_event_details,
                "score_event_fit": score_event_fit,
                "rank_event_candidates": rank_event_candidates,
                "generate_campaign_brief": generate_campaign_brief,
                "generate_copy_variants": generate_copy_variants,
                "generate_image_prompt": generate_image_prompt,
                "generate_draft_poster": generate_draft_poster,
            }
        except ImportError:
            self._tools_module = {}

        return self._tools_module


# Singleton instance
_bridge: Optional[MCPBridge] = None


def get_mcp_bridge() -> MCPBridge:
    """Get or create the singleton MCP bridge."""
    global _bridge
    if _bridge is None:
        _bridge = MCPBridge()
    return _bridge
