import urllib.request
import urllib.parse
import json
from mcp.server.fastmcp import FastMCP
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
def play_music(song_name: str) -> str:
    """Search Indian, Punjabi, Bollywood, or English songs and get direct MP3 audio link."""
    try:
        encoded_query = urllib.parse.quote(song_name)
        api_url = f"https://saavn.dev/api/search/songs?query={encoded_query}&limit=1"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            results = data.get("data", {}).get("results", [])
            if not results:
                return f"Could not find any song matching {song_name}."
            
            song = results[0]
            title = song.get("name", song_name)
            artists = song.get("artists", {}).get("primary", [])
            artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
            
            download_urls = song.get("downloadUrl", [])
            if not download_urls:
                return "Audio stream link not available for this song."
            
            # 96kbps ya 160kbps MP3 chunein jo ESP32 par smoothly chale
            mp3_url = download_urls[1]["url"] if len(download_urls) > 1 else download_urls[0]["url"]
            return f"Song: {title} by {artist_name}\nPlayable MP3 URL: {mp3_url}\nTell the user you are playing {title} and stream this MP3 URL."
    except Exception as e:
        return f"Music fetch error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
