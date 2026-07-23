"""Smoke test: start davin-mcp over stdio, list tools, call status + inspect."""

import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command="uv", args=["run", "davin-mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"{len(tools.tools)} tools: {', '.join(t.name for t in tools.tools)}")
            result = await session.call_tool("status", {})
            print("status:", result.content[0].text)
            result = await session.call_tool(
                "build_ranges",
                {
                    "captions": [
                        {"start": 0.0, "end": 2.0, "text": "keep me"},
                        {"start": 2.1, "end": 4.0, "text": "drop me"},
                        {"start": 4.2, "end": 6.0, "text": "keep me too"},
                    ],
                    "drop_matching": "drop",
                },
            )
            print("build_ranges:", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
