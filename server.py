import os
import json
import asyncio
import tempfile
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI
from duckduckgo_search import DDGS
import yt_dlp

app = FastAPI()
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.get("/")
async def root():
    return {"status": "Louis Max Brain Online", "ws_endpoint": "/ws"}

def search_web(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "No search results found."
            return "\n".join([f"{r['title']}: {r['body']}" for r in results])
    except Exception as e:
        return f"Search error: {str(e)}"

def get_song_pcm(song_query: str) -> bytes:
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch1",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song_query, download=False)
            if "entries" in info:
                info = info["entries"][0]
            audio_url = info["url"]

        # Convert first 30 seconds to 16kHz 16-bit Mono PCM for ESP32 MAX98357A
        cmd = [
            "ffmpeg", "-i", audio_url,
            "-t", "30",
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", "pipe:1"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return proc.stdout
    except Exception as e:
        print("Music error:", e)
        return b""

async def text_to_pcm(text: str) -> bytes:
    speech = await client.audio.speech.create(
        model="tts-1",
        voice="onyx",
        input=text,
        response_format="pcm"  # 24kHz 16-bit mono raw PCM
    )
    raw_24k = speech.read()
    # Resample 24kHz -> 16kHz via ffmpeg for ESP32 speaker
    cmd = [
        "ffmpeg", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "pipe:0",
        "-f", "s16le", "-ar", "16000", "-ac", "1", "pipe:1"
    ]
    proc = subprocess.run(cmd, input=raw_24k, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return proc.stdout

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("ESP32 Louis Max Connected!")
    await ws.send_text(json.dumps({"status": "Online! Listening..."}))

    try:
        while True:
            wav_bytes = await ws.receive_bytes()
            await ws.send_text(json.dumps({"status": "Thinking..."}))

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_bytes)
                tmp_path = tmp.name

            with open(tmp_path, "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            os.remove(tmp_path)
            user_text = transcript.text.strip()
            print("User said:", user_text)

            if not user_text:
                await ws.send_text(json.dumps({"status": "Online! Listening..."}))
                continue

            lower_text = user_text.lower()
            # Volume control
            if "volume" in lower_text:
                vol = 1.0 if ("full" in lower_text or "max" in lower_text or "100" in lower_text) else (0.3 if "low" in lower_text else 0.7)
                await ws.send_text(json.dumps({"volume": vol}))
                reply = f"Volume set to {int(vol * 100)} percent."
                pcm = await text_to_pcm(reply)
                await ws.send_bytes(pcm)
                await ws.send_text(json.dumps({"status": "Online! Listening..."}))
                continue

            # Music playback
            if any(k in lower_text for k in ["play ", "song", "gaana", "music"]):
                await ws.send_text(json.dumps({"status": "Loading Song..."}))
                pcm_song = await asyncio.to_thread(get_song_pcm, user_text)
                if pcm_song:
                    await ws.send_text(json.dumps({"status": "Playing Music..."}))
                    for i in range(0, len(pcm_song), 4096):
                        await ws.send_bytes(pcm_song[i:i+4096])
                        await asyncio.sleep(0.08)
                else:
                    pcm = await text_to_pcm("Sorry, I could not load that song right now.")
                    await ws.send_bytes(pcm)
                await ws.send_text(json.dumps({"status": "Online! Listening..."}))
                continue

            # Web search + AI answer
            context = ""
            if any(k in lower_text for k in ["search", "news", "weather", "latest", "who is", "what is", "score", "price", "today", "aaj", "kya hai"]):
                await ws.send_text(json.dumps({"status": "Searching Web..."}))
                context = await asyncio.to_thread(search_web, user_text)

            messages = [
                {"role": "system", "content": "You are Louis Max, a helpful, witty voice AI assistant running on an ESP32 hardware device. Keep answers concise (2-3 short sentences) suitable for spoken voice output."},
                {"role": "user", "content": f"User query: {user_text}\nWeb context (if any): {context}"}
            ]
            completion = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            reply_text = completion.choices[0].message.content
            print("Louis Max:", reply_text)

            await ws.send_text(json.dumps({"status": "Speaking..."}))
            pcm_reply = await text_to_pcm(reply_text)
            for i in range(0, len(pcm_reply), 4096):
                await ws.send_bytes(pcm_reply[i:i+4096])
                await asyncio.sleep(0.08)

            await ws.send_text(json.dumps({"status": "Online! Listening..."}))

    except WebSocketDisconnect:
        print("ESP32 disconnected")
