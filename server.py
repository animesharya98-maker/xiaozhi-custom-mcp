import os
import sys
import asyncio
import websockets
from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS

mcp = FastMCP("IndiaSearch")

@mcp.tool()
def search_india(query: str) -> str:
    """Search Google/DuckDuckGo for latest news, weather, places, and facts in India."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, region="in-en", max_results=3))
    if not results:
        return "No results found."
    return "\n\n".join(f"{r['title']}: {r['body']}" for r in results)

async def bridge():
    uri = os.environ.get("MCP_ENDPOINT")
    if not uri:
        print("MCP_ENDPOINT missing!")
        return
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-u", __file__, "--stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    async with websockets.connect(uri, ping_interval=20) as ws:
        async def ws_to_proc():
            async for msg in ws:
                proc.stdin.write((msg + "\n").encode())
                await proc.stdin.drain()

        async def proc_to_ws():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                await ws.send(line.decode().strip())

        await asyncio.gather(ws_to_proc(), proc_to_ws())

if __name__ == "__main__":
    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        asyncio.run(bridge())
