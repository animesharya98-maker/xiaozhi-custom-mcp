import urllib.request
import urllib.parse
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("IndianWebSearch")

@mcp.tool()
def search_web(query: str) -> str:
    """Search the internet for Indian schools, places, news, singers, or facts."""
    results_list = []
    encoded = urllib.parse.quote(query)

    # 1. Wikipedia Search API (Fast & Reliable)
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&format=json&utf8=1"
        req = urllib.request.Request(wiki_url, headers={'User-Agent': 'XiaozhiAssistant/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            wiki_data = json.loads(resp.read().decode('utf-8'))
            for item in wiki_data.get("query", {}).get("search", [])[:3]:
                snippet = item['snippet'].replace('<span class="searchmatch">', '').replace('</span>', '')
                results_list.append(f"- Wikipedia ({item['title']}): {snippet}")
    except Exception:
        pass

    # 2. DuckDuckGo Instant Answer API (Zero dependency)
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(ddg_url, headers={'User-Agent': 'XiaozhiAssistant/1.0'})
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

if __name__ == "__main__":
    mcp.run(transport="stdio")
