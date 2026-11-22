import asyncio
import websockets
import subprocess
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

MCP_ENDPOINT = os.environ.get("MCP_ENDPOINT")

# Render Web Service ko active rakhne ke liye dummy port
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Xiaozhi MCP Bridge is Running!")
    def log_message(self, format, *args):
        pass

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

async def pipe_stdio_to_ws(ws, process):
    async def read_stdout():
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            await ws.send(line.decode('utf-8'))

    async def write_stdin():
        async for message in ws:
            if isinstance(message, str):
                process.stdin.write((message + "\n").encode('utf-8'))
                await process.stdin.drain()

    await asyncio.gather(read_stdout(), write_stdin())

async def main():
    if not MCP_ENDPOINT:
        print("Error: MCP_ENDPOINT environment variable is missing.")
        sys.exit(1)
    while True:
        try:
            async with websockets.connect(MCP_ENDPOINT) as ws:
                print("Connected to Xiaozhi MCP Endpoint!")
                process = await asyncio.create_subprocess_exec(
                    sys.executable, sys.argv[1],
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=sys.stderr
                )
                await pipe_stdio_to_ws(ws, process)
        except Exception as e:
            print(f"Connection lost: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=start_dummy_server, daemon=True).start()
    asyncio.run(main())
