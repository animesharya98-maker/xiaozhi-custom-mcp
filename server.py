import os
import asyncio
from mcp.server.fastmcp import FastMCP
import yt_dlp
from duckduckgo_search import DDGS

mcp = FastMCP("CustomMusicAndSearch")

@mcp.tool()
def search_web(query: str) -> str:
    """Search the internet for places, news, facts, or general information."""
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            return "No results found."
        summary = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
        return summary
    except Exception as e:
        return f"Search error: {str(e)}"

@mcp.tool()
def play_youtube_music(song_name: str) -> str:
    """Search a song on YouTube and get its direct playable audio stream URL."""
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch1'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song_name, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            title = info.get('title', song_name)
            audio_url = info.get('url', '')
            return f"Song Found: {title}\nAudio Stream URL: {audio_url}\nInstruction: Play this audio URL directly on the device."
    except Exception as e:
        return f"Could not fetch song: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")