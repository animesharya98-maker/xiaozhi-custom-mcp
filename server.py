import asyncio
import json
import os
import sys
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
import websockets

MCP_ENDPOINT = os.environ.get("MCP_ENDPOINT")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Xiaozhi MCP Server is Live!")
    def log_message(self, format, *args):
        pass

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

def search_web(query: str) -> str:
    results_list = []
    encoded = urllib.parse.quote(query)

    # 1. Wikipedia Search
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&format=json&utf8=1"
        req = urllib.request.Request(wiki_url, headers={'User-Agent': 'XiaozhiBot/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            wiki_data = json.loads(resp.read().decode('utf-8'))
            for item in wiki_data.get("query", {}).get("search", [])[:3]:
                snippet = item['snippet'].replace('<span class="searchmatch">', '').replace('</span>', '')
                results_list.append(f"- Wikipedia ({item['title']}): {snippet}")
    except Exception:
        pass

    # 2. DuckDuckGo Instant API
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(ddg_url, headers={'User-Agent': 'XiaozhiBot/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            ddg_data = json.loads(resp.read().decode('utf-8'))
            if ddg_data.get("AbstractText"):
                results_list.append(f"- Summary: {ddg_data['AbstractText']}")
            for topic in ddg_data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results_list.append(f"- Info: {topic['Text']}")
    except Exception:
        pass

    if not results_list:
        return "No exact information found on Wikipedia or DuckDuckGo for this query."
    return "\n".join(results_list)

async def handle_mcp():
    if not MCP_ENDPOINT:
        print("Error: MCP_ENDPOINT is missing!")
        sys.exit(1)

    while True:
        try:
            async with websockets.connect(MCP_ENDPOINT) as ws:
                print("Connected to Xiaozhi MCP Endpoint!")
                async for raw_msg in ws:
                    msg = json.loads(raw_msg)
                    msg_id = msg.get("id")
                    method = msg.get("method")

                    if method == "initialize":
                        resp = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {"tools": {}},
                                "serverInfo": {"name": "IndianWebSearch", "version": "1.0"}
                            }
                        }
                        await ws.send(json.dumps(resp))

                    elif method == "tools/list":
                        resp = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "tools": [
                                    {
                                        "name": "search_web",
                                        "description": "Search the internet for Indian schools, places, news, singers, or facts.",
                                        "inputSchema": {
                                            "type": "object",
                                            "properties": {
                                                "query": {"type": "string", "description": "Search query"}
                                            },
                                            "required": ["query"]
                                        }
                                    }
                                ]
                            }
                        }
                        await ws.send(json.dumps(resp))

                    elif method == "tools/call":
                        args = msg.get("params", {}).get("arguments", {})
                        query = args.get("query", "")
                        output = await asyncio.to_thread(search_web, query)
                        resp = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "content": [{"type": "text", "text": output}]
                            }
                        }
                        await ws.send(json.dumps(resp))

        except Exception as e:
            print(f"Reconnecting in 5s due to: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=start_dummy_server, daemon=True).start()
    asyncio.run(handle_mcp())
